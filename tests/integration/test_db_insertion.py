import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy.exc import OperationalError
from src.db.connection import init_db, SessionLocal
from src.db.models import Transaction, ProcessedFile
from src.pipeline.loader_db import process_and_load_content as process_and_insert_csv

@pytest.fixture(autouse=True)
def setup_db():
    init_db()

def test_insertion_and_flag():
    csv_data = (
        "datetime_transaction,iban_origine,pays_source,banque_source,iban_destinataire,pays_destinataire,montant\n"
        "2026-01-15 10:00:00,FR01,FR,BNP,DE01,DE,6200.0\n"
        "2026-01-15 10:30:00,FR01,FR,BNP,IT01,IT,150.0\n"
    )
    filename = "test_run_1.csv"

    success = process_and_insert_csv(filename, csv_data)
    assert success is True

    session = SessionLocal()
    transactions = session.query(Transaction).filter_by(source_file=filename).all()
    assert len(transactions) == 2

    # Vérification du flag > 5000
    t_high = [t for t in transactions if t.montant == 6200.0][0]
    t_low = [t for t in transactions if t.montant == 150.0][0]
    assert t_high.is_high_value is True
    assert t_low.is_high_value is False

    session.close()

def test_anti_duplicate_mechanism():
    csv_data = (
        "datetime_transaction,iban_origine,pays_source,banque_source,iban_destinataire,pays_destinataire,montant\n"
        "2026-01-15 11:00:00,DE01,DE,DB,FR01,FR,800.0\n"
    )
    filename = "unique_file.csv"

    # Premier passage : traité
    assert process_and_insert_csv(filename, csv_data) is True

    # Deuxième passage (même nom et même contenu) : ignoré
    assert process_and_insert_csv(filename, csv_data) is False

    session = SessionLocal()
    recorded_files = session.query(ProcessedFile).filter_by(filename=filename).all()
    assert len(recorded_files) == 1
    session.close()

def test_retry_on_db_transient_failure():
    csv_data = (
        "datetime_transaction,iban_origine,pays_source,banque_source,iban_destinataire,pays_destinataire,montant\n"
        "2026-01-15 12:00:00,ES01,ES,Santander,FR01,FR,950.0\n"
    )
    filename = "test_retry.csv"

    attempts = {"count": 0}
    real_session = SessionLocal()

    def flaky_commit():
        attempts["count"] += 1
        if attempts["count"] < 3:
            # Simule 2 pannes temporaires de connexion
            raise OperationalError("Connection temporarily lost", params=None, orig=Exception("DB drop"))
        real_session.commit()

    with patch("src.pipeline.loader_db.SessionLocal") as mock_session_maker:
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.first.return_value = None
        mock_session.commit.side_effect = flaky_commit
        mock_session_maker.return_value = mock_session

        res = process_and_insert_csv(filename, csv_data)
        assert res is True
        # Vérifie qu'il y a bien eu 3 tentatives grâce au décorateur @retry
        assert attempts["count"] == 3