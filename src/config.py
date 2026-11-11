"""Configuration centralisée (variables d'environnement)."""
import os

DB_URL = os.getenv(
    "DB_URL", "postgresql://pipeline_user:pipeline_password@localhost:5432/financial_db"
)
S3_ENDPOINT = os.getenv("S3_ENDPOINT", "http://localhost:9000")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "minioadmin")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "minioadminpassword")
S3_BUCKET = os.getenv("S3_BUCKET", "transactions-bucket")

# Retry (valable pour la base et pour S3)
RETRY_MAX_ATTEMPTS = int(os.getenv("RETRY_MAX_ATTEMPTS", "3"))
RETRY_WAIT_SECONDS = float(os.getenv("RETRY_WAIT_SECONDS", "2"))

# Option 3 : petit modèle de langage local (Ollama)
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")
