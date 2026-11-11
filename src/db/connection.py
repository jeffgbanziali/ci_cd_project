from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.config import DB_URL
from src.db.models import Base

engine = create_engine(DB_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)