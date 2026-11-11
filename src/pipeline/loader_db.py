import hashlib
import logging
import io
import pandas as pd
from sqlalchemy.exc import OperationalError, DatabaseError
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from src.db.connection import SessionLocal
from src.db.models import ProcessedFile, Transaction, AggregationSourceIban, AggregationSourceBank, AggregationDestIban
from src.pipeline.transformer import (
    flag_high_value_transactions,
    sum_amount_by_iban_origine,
    sum_amount_by_banque_source,
    sum_amount_by_iban_destinataire
)

logger = logging.getLogger(__name__)

def compute_hash(content: str) -> str:
    return hashlib.sha256(content.encode('utf-8')).hexdigest()

@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(2),
    retry=retry_if_exception_type((OperationalError, DatabaseError)),
    reraise=True
)
def process_and_load_content(filename: str, content: str) -> bool:
    content_hash = compute_hash(content)
    session = SessionLocal()

    try:
        # 1. Vérification Anti-doublon (Idempotence)
        existing = session.query(ProcessedFile).filter(
            (ProcessedFile.filename == filename) | (ProcessedFile.content_hash == content_hash)
        ).first()

        if existing:
            logger.warning(f"Fichier {filename} déjà traité avec succès. Ignoré.")
            return False

        # 2. Parsing et Traitements purs
        df_raw = pd.read_csv(io.StringIO(content))
        df_processed = flag_high_value_transactions(df_raw)
        agg_source_iban = sum_amount_by_iban_origine(df_raw)
        agg_source_bank = sum_amount_by_banque_source(df_raw)
        agg_dest_iban = sum_amount_by_iban_destinataire(df_raw)

        # 3. Insertions en base dans une transaction atomique
        for _, row in df_processed.iterrows():
            session.add(Transaction(
                datetime_transaction=pd.to_datetime(row['datetime_transaction']),
                iban_origine=row['iban_origine'],
                pays_source=row['pays_source'],
                banque_source=row['banque_source'],
                iban_destinataire=row['iban_destinataire'],
                pays_destinataire=row['pays_destinataire'],
                montant=float(row['montant']),
                is_high_value=bool(row['is_high_value']),
                source_file=filename
            ))

        for _, row in agg_source_iban.iterrows():
            session.add(AggregationSourceIban(iban_origine=row['iban_origine'], total_envoye=float(row['total_envoye'])))

        for _, row in agg_source_bank.iterrows():
            session.add(AggregationSourceBank(banque_source=row['banque_source'], total_envoye=float(row['total_envoye'])))

        for _, row in agg_dest_iban.iterrows():
            session.add(AggregationDestIban(iban_destinataire=row['iban_destinataire'], total_recu=float(row['total_recu'])))

        # 4. Enregistrement du fichier dans l'index des fichiers traités
        session.add(ProcessedFile(filename=filename, content_hash=content_hash))

        session.commit()
        logger.info(f"Fichier {filename} traité et inséré en base avec succès.")
        return True

    except Exception as e:
        session.rollback()
        logger.error(f"Erreur d'insertion pour {filename}: {e}. Rollback exécuté.")
        raise
    finally:
        session.close()