from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class ProcessedFile(Base):
    __tablename__ = "processed_files"
    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(255), unique=True, nullable=False)
    content_hash = Column(String(64), unique=True, nullable=False)
    processed_at = Column(DateTime, default=datetime.utcnow)

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    datetime_transaction = Column(DateTime, nullable=False)
    iban_origine = Column(String(34), nullable=False)
    pays_source = Column(String(2), nullable=False)
    banque_source = Column(String(100), nullable=False)
    iban_destinataire = Column(String(34), nullable=False)
    pays_destinataire = Column(String(2), nullable=False)
    montant = Column(Float, nullable=False)
    is_high_value = Column(Boolean, nullable=False)
    source_file = Column(String(255), nullable=False)

class AggregationSourceIban(Base):
    __tablename__ = "agg_iban_source"
    id = Column(Integer, primary_key=True, autoincrement=True)
    iban_origine = Column(String(34), nullable=False)
    total_envoye = Column(Float, nullable=False)
    calculated_at = Column(DateTime, default=datetime.utcnow)

class AggregationSourceBank(Base):
    __tablename__ = "agg_bank_source"
    id = Column(Integer, primary_key=True, autoincrement=True)
    banque_source = Column(String(100), nullable=False)
    total_envoye = Column(Float, nullable=False)
    calculated_at = Column(DateTime, default=datetime.utcnow)

class AggregationDestIban(Base):
    __tablename__ = "agg_iban_dest"
    id = Column(Integer, primary_key=True, autoincrement=True)
    iban_destinataire = Column(String(34), nullable=False)
    total_recu = Column(Float, nullable=False)
    calculated_at = Column(DateTime, default=datetime.utcnow)