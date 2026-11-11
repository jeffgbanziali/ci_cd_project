"""Configuration des tests.

SÉCURITÉ : les tests utilisent TEST_DB_URL / TEST_S3_ENDPOINT (jamais DB_URL de prod, car les
tests vident la base). Sans ces variables : SQLite temporaire + serveur S3 simulé (moto), ce qui
permet de lancer les tests partout sans Docker. En CI : vraies bases Postgres + S3 (SeaweedFS).

Ce fichier est importé AVANT `src` : il fixe donc l'environnement lu par src.config.
"""
import os
import socket
import tempfile

import pytest

_tmpdir = tempfile.mkdtemp(prefix="pipeline-tests-")
_moto_server = None

os.environ["DB_URL"] = os.getenv("TEST_DB_URL", f"sqlite:///{_tmpdir}/test.db")
os.environ["RETRY_WAIT_SECONDS"] = "0"
os.environ["RETRY_MAX_ATTEMPTS"] = "3"
os.environ["S3_BUCKET"] = "transactions-test"
os.environ.pop("SIMULATE_DB_FAILURES", None)
os.environ.pop("SIMULATE_S3_FAILURES", None)

if os.getenv("TEST_S3_ENDPOINT"):
    os.environ["S3_ENDPOINT"] = os.environ["TEST_S3_ENDPOINT"]
    os.environ["S3_ACCESS_KEY"] = os.getenv("TEST_S3_ACCESS_KEY", "minioadmin")
    os.environ["S3_SECRET_KEY"] = os.getenv("TEST_S3_SECRET_KEY", "minioadminpassword")
else:
    from moto.server import ThreadedMotoServer

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        _port = sock.getsockname()[1]
    _moto_server = ThreadedMotoServer(ip_address="127.0.0.1", port=_port, verbose=False)
    _moto_server.start()
    os.environ["S3_ENDPOINT"] = f"http://127.0.0.1:{_port}"
    os.environ["S3_ACCESS_KEY"] = "test"
    os.environ["S3_SECRET_KEY"] = "test"


def pytest_unconfigure(config):
    if _moto_server is not None:
        _moto_server.stop()


def pytest_collection_modifyitems(items):
    for item in items:
        if "integration" in str(item.fspath).replace("\\", "/").split("/tests/")[-1]:
            item.add_marker(pytest.mark.integration)
