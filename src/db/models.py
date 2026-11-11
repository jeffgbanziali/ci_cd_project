"""Schéma relationnel.

processed_files ──< transactions
              ├──< agg_iban_source
              ├──< agg_bank_source
              └──< agg_iban_dest
"""
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String,
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ProcessedFile(Base):
    """Un fichier traité avec succès. content_hash UNIQUE => jamais traité deux fois."""

    __tablename__ = "processed_files"
    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(255), nullable=False)
    content_hash = Column(String(64), unique=True, nullable=False)
    transaction_count = Column(Integer, nullable=False)
    processed_at = Column(DateTime(timezone=True), default=_now, nullable=False)


class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    file_id = Column(Integer, ForeignKey("processed_files.id"), nullable=False, index=True)
    datetime_transaction = Column(DateTime, nullable=False)
    iban_origine = Column(String(34), nullable=False)
    pays_source = Column(String(2), nullable=False)
    banque_source = Column(String(100), nullable=False)
    iban_destinataire = Column(String(34), nullable=False)
    pays_destinataire = Column(String(2), nullable=False)
    montant = Column(Numeric(16, 2), nullable=False)  # Numeric, jamais Float pour de l'argent
    is_high_value = Column(Boolean, nullable=False)


class AggregationSourceIban(Base):
    __tablename__ = "agg_iban_source"
    id = Column(Integer, primary_key=True, autoincrement=True)
    file_id = Column(Integer, ForeignKey("processed_files.id"), nullable=False, index=True)
    iban_origine = Column(String(34), nullable=False)
    total_envoye = Column(Numeric(18, 2), nullable=False)


class AggregationSourceBank(Base):
    __tablename__ = "agg_bank_source"
    id = Column(Integer, primary_key=True, autoincrement=True)
    file_id = Column(Integer, ForeignKey("processed_files.id"), nullable=False, index=True)
    banque_source = Column(String(100), nullable=False)
    total_envoye = Column(Numeric(18, 2), nullable=False)


class AggregationDestIban(Base):
    __tablename__ = "agg_iban_dest"
    id = Column(Integer, primary_key=True, autoincrement=True)
    file_id = Column(Integer, ForeignKey("processed_files.id"), nullable=False, index=True)
    iban_destinataire = Column(String(34), nullable=False)
    total_recu = Column(Numeric(18, 2), nullable=False)
