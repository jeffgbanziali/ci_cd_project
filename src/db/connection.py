from sqlalchemy import create_engine
from sqlalchemy.exc import InterfaceError, OperationalError
from sqlalchemy.orm import sessionmaker
from tenacity import Retrying, retry_if_exception_type, stop_after_attempt, wait_fixed

from src.config import DB_URL
from src.db.models import Base
from src.errors import TransientError

engine = create_engine(DB_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Crée les tables si besoin (idempotent)."""
    Base.metadata.create_all(bind=engine)


def init_db_with_retry(max_attempts: int = 10, wait_seconds: float = 2.0) -> None:
    """Attend que la base soit disponible (démarrage du conteneur Postgres)."""
    for attempt in Retrying(
        stop=stop_after_attempt(max_attempts),
        wait=wait_fixed(wait_seconds),
        retry=retry_if_exception_type((OperationalError, InterfaceError, TransientError)),
        reraise=True,
    ):
        with attempt:
            init_db()


def reset_db() -> None:
    """Repart d'une base vide (utilisé par les tests)."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
