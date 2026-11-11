import logging
from src.db.connection import init_db
from src.storage.s3_client import S3Manager
from src.pipeline.generator import generate_csv_files
from src.pipeline.loader_db import process_and_load_content

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def run_pipeline():
    logging.info("1. Initialisation de la base de données...")
    init_db()

    logging.info("2. Configuration du stockage S3...")
    s3 = S3Manager()
    s3.ensure_bucket_exists()

    logging.info("3. Génération des fichiers CSV...")
    files = generate_csv_files(num_files=2)

    logging.info("4. Envoi des fichiers CSV vers le bucket S3...")
    for fpath in files:
        fname = fpath.replace("\\", "/").split("/")[-1]
        s3.upload_file(fpath, fname)

    logging.info("5. Récupération depuis S3, transformation et insertion en base...")
    remote_files = s3.list_files()
    for fname in remote_files:
        content = s3.get_file_content(fname)
        process_and_load_content(fname, content)

    logging.info("Pipeline S3 validée avec succès !")

if __name__ == "__main__":
    run_pipeline()