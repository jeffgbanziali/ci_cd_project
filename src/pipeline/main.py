"""Orchestration : python -m src.pipeline.main [--process-only | --schedule N | --ingest-text T]."""
import argparse
import logging
import sys
import tempfile
import time
from collections.abc import Callable

from src.db.connection import init_db_with_retry
from src.errors import InvalidDataError
from src.pipeline.generator import generate_csv_files
from src.pipeline.loader_db import process_and_load_content
from src.pipeline.slm_extractor import ingest_text
from src.storage.s3_client import S3Manager

logger = logging.getLogger("pipeline")


def process_pending(s3: S3Manager) -> tuple[int, int]:
    """S3 -> récupération (retry) -> chargement -> traitement -> BDD (retry).

    - panne d'infrastructure définitive (retry épuisé) : arrêt immédiat de la pipeline ;
    - fichier invalide : il est signalé, les autres fichiers continuent d'être traités
      (un fichier corrompu ne doit pas bloquer les suivants), puis la pipeline échoue à la fin.
    Retourne (traités, ignorés).
    """
    processed = skipped = 0
    invalid: list[str] = []
    for name in s3.list_files():
        content = s3.get_file_content(name)
        try:
            inserted = process_and_load_content(name, content)
        except InvalidDataError as exc:
            logger.error("Fichier invalide, ignoré : %s", exc)
            invalid.append(str(exc))
            continue
        if inserted:
            processed += 1
        else:
            skipped += 1
    logger.info("Bilan : %d traité(s), %d ignoré(s), %d invalide(s).",
                processed, skipped, len(invalid))
    if invalid:
        raise InvalidDataError(f"{len(invalid)} fichier(s) invalide(s) : " + " | ".join(invalid))
    return processed, skipped


def run_pipeline() -> None:
    """Pipeline complète de bout en bout."""
    s3 = S3Manager()
    logger.info("1/6 Attente du service S3 et de la base de données...")
    s3.wait_until_ready()
    init_db_with_retry()

    logger.info("2/6 Configuration du bucket S3...")
    s3.ensure_bucket_exists()

    logger.info("3/6 Génération des fichiers CSV...")
    with tempfile.TemporaryDirectory() as tmp:
        files = generate_csv_files(output_dir=tmp, num_files=3)

        logger.info("4/6 Envoi des CSV vers le bucket S3...")
        names = []
        for path in files:
            name = path.replace("\\", "/").split("/")[-1]
            s3.upload_file(path, name)
            names.append(name)

    logger.info("5/6 Vérification de la présence des fichiers dans S3...")
    s3.verify_files_present(names)

    logger.info("6/6 Récupération depuis S3, traitement et insertion en base...")
    process_pending(s3)
    logger.info("Pipeline terminée avec succès.")


def run_scheduler(interval: float, max_runs: int | None = None,
                  sleep: Callable[[float], None] = time.sleep) -> None:
    """Option 1 (CD) : traite régulièrement les NOUVEAUX fichiers déposés dans S3."""
    s3 = S3Manager()
    s3.wait_until_ready()
    s3.ensure_bucket_exists()
    init_db_with_retry()
    runs = 0
    while max_runs is None or runs < max_runs:
        runs += 1
        logger.info("=== Cycle %d : recherche de nouveaux fichiers ===", runs)
        try:
            process_pending(s3)
        except Exception:  # un cycle en échec ne doit pas arrêter le scheduler
            logger.exception("Cycle %d en échec, nouvel essai au prochain passage.", runs)
        if max_runs is None or runs < max_runs:
            sleep(interval)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    parser = argparse.ArgumentParser(prog="pipeline")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--process-only", action="store_true",
                       help="traite uniquement les fichiers déjà présents dans S3")
    group.add_argument("--schedule", type=float, metavar="SECONDES",
                       help="traitement périodique (Option 1 : CD)")
    group.add_argument("--ingest-text", metavar="TEXTE",
                       help="extraction d'une transaction depuis du texte via un SLM (Option 3)")
    args = parser.parse_args(argv)

    try:
        if args.schedule:
            run_scheduler(args.schedule)
        elif args.ingest_text:
            init_db_with_retry()
            ingest_text(args.ingest_text)
        elif args.process_only:
            s3 = S3Manager()
            s3.wait_until_ready()
            init_db_with_retry()
            process_pending(s3)
        else:
            run_pipeline()
    except Exception:
        logger.exception("PIPELINE EN ÉCHEC")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
