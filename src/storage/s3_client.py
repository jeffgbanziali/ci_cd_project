import logging
import boto3
from botocore.exceptions import ClientError, EndpointConnectionError
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from src.config import S3_ENDPOINT, S3_ACCESS_KEY, S3_SECRET_KEY, S3_BUCKET

logger = logging.getLogger(__name__)

class S3Manager:
    def __init__(self):
        self.client = boto3.client(
            "s3",
            endpoint_url=S3_ENDPOINT,
            aws_access_key_id=S3_ACCESS_KEY,
            aws_secret_access_key=S3_SECRET_KEY,
            region_name="us-east-1"
        )
        self.bucket = S3_BUCKET

    def ensure_bucket_exists(self):
        try:
            self.client.head_bucket(Bucket=self.bucket)
        except ClientError:
            self.client.create_bucket(Bucket=self.bucket)
            logger.info(f"Bucket {self.bucket} créé.")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(2),
        retry=retry_if_exception_type((ClientError, EndpointConnectionError)),
        reraise=True
    )
    def upload_file(self, local_path: str, remote_filename: str):
        logger.info(f"Envoi de {local_path} vers s3://{self.bucket}/{remote_filename}")
        self.client.upload_file(local_path, self.bucket, remote_filename)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(2),
        retry=retry_if_exception_type((ClientError, EndpointConnectionError)),
        reraise=True
    )
    def get_file_content(self, remote_filename: str) -> str:
        logger.info(f"Récupération de s3://{self.bucket}/{remote_filename}")
        response = self.client.get_object(Bucket=self.bucket, Key=remote_filename)
        return response['Body'].read().decode('utf-8')

    def list_files(self) -> list[str]:
        try:
            response = self.client.list_objects_v2(Bucket=self.bucket)
            return [item['Key'] for item in response.get('Contents', []) if item['Key'].endswith('.csv')]
        except Exception as e:
            logger.error(f"Erreur lors du listing S3: {e}")
            return []