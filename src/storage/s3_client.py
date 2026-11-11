"""Accès S3 (SeaweedFS ici ; tout service compatible S3 fonctionne)."""
import logging

import boto3
from botocore.config import Config
from botocore.exceptions import (
    ClientError, ConnectionClosedError, ConnectTimeoutError, EndpointConnectionError,
    ReadTimeoutError,
)
from tenacity import (
    Retrying, before_sleep_log, retry, retry_if_exception, stop_after_attempt, wait_exponential,
    wait_fixed,
)

from src import chaos
from src.config import (
    RETRY_MAX_ATTEMPTS, RETRY_WAIT_SECONDS, S3_ACCESS_KEY, S3_BUCKET, S3_ENDPOINT, S3_SECRET_KEY,
)
from src.errors import PipelineError, TransientError

logger = logging.getLogger(__name__)

TRANSIENT_CODES = {"RequestTimeout", "SlowDown", "ServiceUnavailable", "InternalError", "Throttling"}


def is_transient(exc: BaseException) -> bool:
    """Seules les pannes TEMPORAIRES sont retentées (pas NoSuchKey, AccessDenied...)."""
    if isinstance(exc, (TransientError, EndpointConnectionError, ConnectTimeoutError,
                        ReadTimeoutError, ConnectionClosedError)):
        return True
    if isinstance(exc, ClientError):
        status = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode", 0)
        code = exc.response.get("Error", {}).get("Code", "")
        return status >= 500 or code in TRANSIENT_CODES
    return False


def _s3_retry():
    return retry(
        stop=stop_after_attempt(RETRY_MAX_ATTEMPTS),
        wait=wait_exponential(multiplier=RETRY_WAIT_SECONDS, max=30),
        retry=retry_if_exception(is_transient),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )


class S3Manager:
    def __init__(self, endpoint: str = S3_ENDPOINT, access_key: str = S3_ACCESS_KEY,
                 secret_key: str = S3_SECRET_KEY, bucket: str = S3_BUCKET):
        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name="us-east-1",
            config=Config(
                signature_version="s3v4",
                s3={"addressing_style": "path"},
                retries={"max_attempts": 0},  # le retry est géré par tenacity (visible dans les logs)
                connect_timeout=5,
                read_timeout=30,
            ),
        )
        self.bucket = bucket

    def wait_until_ready(self, max_attempts: int = 30, wait_seconds: float = 2.0) -> None:
        """Attend que le service S3 soit joignable (démarrage du conteneur)."""
        for attempt in Retrying(
            stop=stop_after_attempt(max_attempts),
            wait=wait_fixed(wait_seconds),
            retry=retry_if_exception(is_transient),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True,
        ):
            with attempt:
                self.client.list_buckets()
        logger.info("Service S3 disponible.")

    def ensure_bucket_exists(self) -> None:
        try:
            self.client.head_bucket(Bucket=self.bucket)
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            if code not in ("404", "NoSuchBucket", "NotFound"):
                raise  # erreur d'auth / serveur : ne pas masquer
            self.client.create_bucket(Bucket=self.bucket)
            logger.info("Bucket %s créé.", self.bucket)

    @_s3_retry()
    def upload_file(self, local_path: str, remote_filename: str) -> None:
        logger.info("Envoi de %s vers s3://%s/%s", local_path, self.bucket, remote_filename)
        self.client.upload_file(local_path, self.bucket, remote_filename)

    @_s3_retry()
    def get_file_content(self, remote_filename: str) -> str:
        logger.info("Récupération de s3://%s/%s", self.bucket, remote_filename)
        chaos.maybe_fail("s3")  # panne temporaire simulée (SIMULATE_S3_FAILURES)
        response = self.client.get_object(Bucket=self.bucket, Key=remote_filename)
        return response["Body"].read().decode("utf-8")

    @_s3_retry()
    def list_files(self) -> list[str]:
        """Liste les CSV du bucket. Les erreurs REMONTENT (on ne renvoie jamais [] en cas de panne)."""
        keys: list[str] = []
        paginator = self.client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket):
            keys.extend(o["Key"] for o in page.get("Contents", []) if o["Key"].endswith(".csv"))
        return sorted(keys)

    def verify_files_present(self, expected: list[str]) -> None:
        present = set(self.list_files())
        missing = sorted(set(expected) - present)
        if missing:
            raise PipelineError(f"Fichiers absents du bucket '{self.bucket}' : {missing}")
        logger.info("Vérification OK : %d fichier(s) présent(s) dans le bucket.", len(expected))
