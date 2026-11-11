FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src

RUN useradd --create-home appuser
USER appuser

# Sans argument : pipeline complète. Exemples :
#   --process-only     traite les fichiers déjà présents dans S3
#   --schedule 300     traitement périodique (production)
ENTRYPOINT ["python", "-m", "src.pipeline.main"]
