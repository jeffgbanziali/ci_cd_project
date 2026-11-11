"""Insertion en base : atomique, idempotente, avec retry sur pannes TEMPORAIRES uniquement."""
import hashlib
import logging
from decimal import Decimal

from sqlalchemy.exc import IntegrityError, InterfaceError, OperationalError
from tenacity import (
    before_sleep_log, retry, retry_if_exception_type, stop_after_attempt, wait_exponential,
)

from src import chaos
from src.config import RETRY_MAX_ATTEMPTS, RETRY_WAIT_SECONDS
from src.db.connection import SessionLocal
from src.db.models import (
    AggregationDestIban, AggregationSourceBank, AggregationSourceIban, ProcessedFile,
    Transaction,
)
from src.errors import TransientError
from src.pipeline.loader import parse_and_validate
from src.pipeline.transformer import ProcessedResult, process_all

logger = logging.getLogger(__name__)

# IntegrityError / ProgrammingError... ne sont PAS retentées : ce ne sont pas des pannes temporaires.
DB_TRANSIENT = (OperationalError, InterfaceError, TransientError)


def compute_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _money(value: float) -> Decimal:
    return Decimal(str(round(float(value), 2)))


def _already_processed(session, content_hash: str) -> bool:
    return session.query(ProcessedFile.id).filter_by(content_hash=content_hash).first() is not None


@retry(
    stop=stop_after_attempt(RETRY_MAX_ATTEMPTS),
    wait=wait_exponential(multiplier=RETRY_WAIT_SECONDS, max=30),
    retry=retry_if_exception_type(DB_TRANSIENT),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def insert_processed(filename: str, content_hash: str, result: ProcessedResult) -> bool:
    """Tout est inséré dans UNE transaction : en cas d'échec, rollback complet (pas de doublon).

    Retourne False (sans rien écrire) si ce contenu a déjà été traité.
    """
    session = SessionLocal()
    try:
        if _already_processed(session, content_hash):
            return False

        processed = ProcessedFile(
            filename=filename, content_hash=content_hash,
            transaction_count=len(result.transactions),
        )
        session.add(processed)
        session.flush()  # récupère processed.id
        file_id = processed.id

        session.add_all(
            Transaction(
                file_id=file_id,
                datetime_transaction=row["datetime_transaction"],
                iban_origine=row["iban_origine"], pays_source=row["pays_source"],
                banque_source=row["banque_source"],
                iban_destinataire=row["iban_destinataire"],
                pays_destinataire=row["pays_destinataire"],
                montant=_money(row["montant"]), is_high_value=bool(row["is_high_value"]),
            )
            for row in result.transactions.to_dict("records")
        )

        # Panne simulée APRÈS des écritures, AVANT le commit : prouve le rollback complet.
        chaos.maybe_fail("db")

        session.add_all(
            AggregationSourceIban(file_id=file_id, iban_origine=r["iban_origine"],
                                  total_envoye=_money(r["total_envoye"]))
            for r in result.by_iban_origine.to_dict("records")
        )
        session.add_all(
            AggregationSourceBank(file_id=file_id, banque_source=r["banque_source"],
                                  total_envoye=_money(r["total_envoye"]))
            for r in result.by_banque_source.to_dict("records")
        )
        session.add_all(
            AggregationDestIban(file_id=file_id, iban_destinataire=r["iban_destinataire"],
                                total_recu=_money(r["total_recu"]))
            for r in result.by_iban_destinataire.to_dict("records")
        )
        session.commit()
        return True
    except IntegrityError:
        session.rollback()
        # Course : un autre processus a inséré le même contenu entre-temps.
        if _already_processed(session, content_hash):
            return False
        raise
    except Exception as exc:
        session.rollback()
        logger.error("Erreur d'insertion pour %s : %s: %s. Rollback exécuté.",
                     filename, type(exc).__name__, exc)
        raise
    finally:
        session.close()


def process_and_load_content(filename: str, content: str) -> bool:
    """Charge -> valide -> traite (fonctions pures) -> insère. True = inséré, False = déjà traité."""
    content_hash = compute_hash(content)
    df = parse_and_validate(content, filename)   # InvalidDataError : jamais retentée
    result = process_all(df)
    inserted = insert_processed(filename, content_hash, result)
    if inserted:
        flagged = int(result.transactions["is_high_value"].sum())
        logger.info("Fichier %s traité : %d transaction(s), %d > 5000.",
                    filename, len(df), flagged)
    else:
        logger.warning("Fichier %s déjà traité avec succès. Ignoré.", filename)
    return inserted
