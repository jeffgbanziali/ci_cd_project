import os

DB_URL = os.getenv("DB_URL", "postgresql://pipeline_user:pipeline_password@localhost:5432/financial_db")
S3_ENDPOINT = os.getenv("S3_ENDPOINT", "http://localhost:9000")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "minioadmin")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "minioadminpassword")
S3_BUCKET = os.getenv("S3_BUCKET", "transactions-bucket")