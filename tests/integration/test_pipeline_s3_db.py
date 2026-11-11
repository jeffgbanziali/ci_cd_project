"""Pipeline complète S3 -> traitement -> base, sur de VRAIES infrastructures
(Postgres + SeaweedFS en CI ; SQLite + moto en local)."""
from decimal import Decimal

import pytest
from sqlalchemy import func

from src import chaos
from src.db.connection import SessionLocal
from src.db.models import (
    AggregationDestIban, AggregationSourceBank, AggregationSourceIban, ProcessedFile, Transaction,
)
from src.errors import InvalidDataError
from src.pipeline.main import process_pending, run_scheduler
from tests import expected


def count(model):
    with SessionLocal() as session:
        return session.query(func.count(model.id)).scalar()


def totals(model, key_col, value_col):
    with SessionLocal() as session:
        return {getattr(r, key_col): getattr(r, value_col) for r in session.query(model).all()}


# ---------- données insérées, valeurs correctes, flags --------------------------------

def test_all_data_is_inserted(s3, uploaded):
    assert process_pending(s3) == (expected.FILE_COUNT, 0)
    assert count(ProcessedFile) == expected.FILE_COUNT
    assert count(Transaction) == expected.TOTAL_TRANSACTIONS
    with SessionLocal() as session:
        per_file = {
            pf.filename: session.query(func.count(Transaction.id))
            .filter(Transaction.file_id == pf.id).scalar()
            for pf in session.query(ProcessedFile).all()
        }
    assert per_file == expected.ROWS_PER_FILE


def test_aggregated_values_are_correct(s3, uploaded):
    process_pending(s3)
    with SessionLocal() as session:
        # Les 3 fichiers ayant des agrégats par fichier, on les cumule pour comparer
        def cumulated(model, key, value):
            out = {}
            for r in session.query(model).all():
                out[getattr(r, key)] = out.get(getattr(r, key), Decimal("0")) + getattr(r, value)
            return out
        assert cumulated(AggregationSourceIban, "iban_origine", "total_envoye") == expected.SENT_BY_IBAN
        assert cumulated(AggregationSourceBank, "banque_source", "total_envoye") == expected.SENT_BY_BANK
        assert cumulated(AggregationDestIban, "iban_destinataire", "total_recu") == expected.RECEIVED_BY_IBAN


def test_flags_are_correct_including_boundary(s3, uploaded):
    process_pending(s3)
    with SessionLocal() as session:
        flagged = session.query(func.count(Transaction.id)).filter(Transaction.is_high_value).scalar()
        assert flagged == expected.TOTAL_FLAGGED
        for amount, should_be_flagged in expected.FLAG_EXPECTATIONS.items():
            rows = session.query(Transaction).filter(Transaction.montant == amount).all()
            assert rows, f"aucune transaction de {amount} en base"
            assert all(r.is_high_value is should_be_flagged for r in rows), amount


# ---------- anti-doublons --------------------------------------------------------------

def test_second_run_does_not_reprocess_anything(s3, uploaded):
    process_pending(s3)
    assert process_pending(s3) == (0, expected.FILE_COUNT)
    assert count(ProcessedFile) == expected.FILE_COUNT
    assert count(Transaction) == expected.TOTAL_TRANSACTIONS


def test_only_new_file_is_processed_on_next_run(s3, uploaded, tmp_path):
    process_pending(s3)
    new = tmp_path / "new.csv"
    new.write_text(
        "datetime_transaction,iban_origine,pays_source,banque_source,iban_destinataire,"
        "pays_destinataire,montant\n"
        "2026-02-01 10:00:00,FR7630004000031234567890143,FR,BNP Paribas,"
        "DE89370400440532013000,DE,42.00\n"
    )
    s3.upload_file(str(new), "new.csv")
    assert process_pending(s3) == (1, expected.FILE_COUNT)
    assert count(Transaction) == expected.TOTAL_TRANSACTIONS + 1


# ---------- retry insertion en base ----------------------------------------------------

def test_db_retry_recovers_and_creates_no_duplicate(s3, uploaded):
    chaos.configure("db", 2)  # 2 pannes AVANT le commit, puis ça marche
    assert process_pending(s3) == (expected.FILE_COUNT, 0)
    assert chaos._remaining["db"] == 0   # les pannes ont bien eu lieu
    assert count(ProcessedFile) == expected.FILE_COUNT
    assert count(Transaction) == expected.TOTAL_TRANSACTIONS   # aucun doublon malgré le retry


def test_db_retry_gives_up_after_max_attempts_and_rolls_back(s3, uploaded):
    chaos.configure("db", 99)
    with pytest.raises(Exception, match="panne temporaire 'db'"):
        process_pending(s3)
    assert chaos._remaining["db"] == 99 - 3          # exactement 3 tentatives
    assert count(ProcessedFile) == 0 and count(Transaction) == 0   # rien d'écrit à moitié


# ---------- retry récupération S3 ------------------------------------------------------

def test_s3_retry_recovers(s3, uploaded):
    chaos.configure("s3", 2)
    assert process_pending(s3) == (expected.FILE_COUNT, 0)
    assert chaos._remaining["s3"] == 0
    assert count(Transaction) == expected.TOTAL_TRANSACTIONS


def test_s3_retry_gives_up_and_stops_cleanly(s3, uploaded):
    chaos.configure("s3", 99)
    with pytest.raises(Exception, match="panne temporaire 's3'"):
        process_pending(s3)
    assert chaos._remaining["s3"] == 99 - 3
    assert count(ProcessedFile) == 0


def test_unreachable_s3_makes_the_pipeline_fail_instead_of_silently_succeeding(s3):
    from src.storage.s3_client import S3Manager
    broken = S3Manager(endpoint="http://127.0.0.1:9")   # rien n'écoute ici
    with pytest.raises(Exception):
        broken.list_files()   # AVANT correction : retournait [] et la pipeline "réussissait"


# ---------- fichier invalide -----------------------------------------------------------

def test_invalid_csv_stops_pipeline_and_inserts_nothing(s3, tmp_path):
    bad = tmp_path / "invalid.csv"
    bad.write_text("datetime_transaction,iban_origine\n2026-01-01 10:00:00,FR76\n")
    s3.upload_file(str(bad), "invalid.csv")
    with pytest.raises(InvalidDataError, match="colonne"):
        process_pending(s3)
    assert count(ProcessedFile) == 0 and count(Transaction) == 0


def test_invalid_file_does_not_block_valid_files_but_pipeline_still_fails(s3, uploaded, tmp_path):
    bad = tmp_path / "aaa_invalid.csv"
    bad.write_text("datetime_transaction,iban_origine\n2026-01-01 10:00:00,FR76\n")
    s3.upload_file(str(bad), "aaa_invalid.csv")   # trié AVANT les fichiers valides
    with pytest.raises(InvalidDataError, match="aaa_invalid.csv"):
        process_pending(s3)
    assert count(ProcessedFile) == expected.FILE_COUNT          # les 3 valides sont traités
    assert count(Transaction) == expected.TOTAL_TRANSACTIONS


# ---------- scheduler (Option 1) ---------------------------------------------------------

def test_scheduler_picks_up_new_files_each_cycle_without_duplicates(s3, uploaded):
    sleeps = []
    run_scheduler(interval=60, max_runs=3, sleep=sleeps.append)
    assert sleeps == [60, 60]
    assert count(ProcessedFile) == expected.FILE_COUNT
    assert count(Transaction) == expected.TOTAL_TRANSACTIONS


# ---------- Option 3 : texte -> SLM -> même flux --------------------------------------------

def test_text_ingestion_joins_the_same_flow_and_is_idempotent():
    import json
    from src.pipeline.slm_extractor import ingest_text

    def fake_llm(_prompt):
        return json.dumps({"datetime_transaction": "2026-09-12T14:30:00",
                           "iban_origine": "FR761234567890", "iban_destinataire": "DE987654321",
                           "montant": 6200, "banque_source": None})

    text = "Le 12 septembre à 14h30, le compte FR761234567890 a envoyé 6200 € vers DE987654321."
    assert ingest_text(text, llm=fake_llm) is True
    assert ingest_text(text, llm=fake_llm) is False        # anti-doublon identique aux CSV
    with SessionLocal() as session:
        t = session.query(Transaction).one()
        assert t.montant == Decimal("6200.00") and t.is_high_value is True
