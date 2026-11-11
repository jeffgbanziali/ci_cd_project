import pytest
from sqlalchemy.exc import OperationalError
from unittest.mock import patch, MagicMock
from src.db.connection import init_db, SessionLocal
from src.db.models import ProcessedFile
from src.pipeline.loader_db import process_and_load_content

@pytest.fixture(autouse=True)
def setup_database():
    init_db()

def test_idempotence_and_anti_duplicate():
    content = "datetime_transaction,iban_origine,pays_source,banque_source,iban_destinataire,pays_destinataire,montant\n2026-01-01 10:00:00,FR01,FR,BNP,DE01,DE,150.0\n"
    filename = "test_duplicate.csv"

    # 1er passage
    first_run = process_and_load_content(filename, content)
    assert first_run is True

    # 2nd passage avec le même nom/contenu
    second_run = process_and_load_content(filename, content)
    assert second_run is False

    session = SessionLocal()
    files = session.query(ProcessedFile).filter_by(filename=filename).all()
    assert len(files) == 1
    session.close()

def test_database_retry_mechanism():
    content = "datetime_transaction,iban_origine,pays_source,banque_source,iban_destinataire,pays_destinataire,montant\n2026-01-01 10:00:00,FR02,FR,BNP,DE02,DE,5500.0\n"
    filename = "test_retry.csv"

    calls = {"count": 0}
    real_session = SessionLocal()

    def flaky_commit():
        calls["count"] += 1
        if calls["count"] < 3:
            raise OperationalError("Connection dropped", params=None, orig=Exception("DB down"))
        real_session.commit()

    with patch("src.pipeline.loader_db.SessionLocal") as mock_session_maker:
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.first.return_value = None
        mock_session.commit.side_effect = flaky_commit
        mock_session_maker.return_value = mock_session

        process_and_load_content(filename, content)
        assert calls["count"] == 3