import pytest

from src import chaos
from src.db.connection import init_db, reset_db
from src.pipeline.generator import generate_csv_files
from src.storage.s3_client import S3Manager


@pytest.fixture(autouse=True)
def clean_state():
    """Base vide + aucune panne simulée avant chaque test (isolation totale)."""
    chaos.reset()
    init_db()
    reset_db()
    yield
    chaos.reset()


@pytest.fixture
def s3():
    manager = S3Manager()
    manager.wait_until_ready(max_attempts=5, wait_seconds=1)
    manager.ensure_bucket_exists()
    # vide le bucket
    listing = manager.client.list_objects_v2(Bucket=manager.bucket).get("Contents", [])
    for obj in listing:
        manager.client.delete_object(Bucket=manager.bucket, Key=obj["Key"])
    return manager


@pytest.fixture
def uploaded(s3, tmp_path):
    """Génère les 3 CSV déterministes et les envoie dans S3."""
    names = []
    for path in generate_csv_files(output_dir=str(tmp_path), num_files=3):
        name = path.replace("\\", "/").split("/")[-1]
        s3.upload_file(path, name)
        names.append(name)
    s3.verify_files_present(names)
    return names
