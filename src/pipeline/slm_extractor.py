"""Option 3 : extraction de transactions depuis du texte brut avec un SLM (Ollama).

Le SLM EXTRAIT (date, IBAN, montant) ; le code DÉDUIT (pays = préfixe IBAN) et VALIDE
(TransactionRow). Le résultat est converti en CSV puis suit EXACTEMENT le même flux que
les fichiers CSV (validation, traitement, insertion, anti-doublon, retry).
"""
import csv
import io
import json
import logging
import urllib.error
import urllib.request
from collections.abc import Callable
from datetime import datetime

from pydantic import ValidationError as PydanticValidationError

from src.config import OLLAMA_MODEL, OLLAMA_URL
from src.errors import InvalidDataError, TransientError
from src.pipeline.loader import COLUMNS, TransactionRow
from src.pipeline.loader_db import compute_hash, process_and_load_content

logger = logging.getLogger(__name__)

PROMPT = """Tu es un extracteur d'informations financières.
Extrais UNE transaction du texte et réponds UNIQUEMENT avec un objet JSON ayant ces clés :
- "datetime_transaction" : date et heure ISO 8601 (YYYY-MM-DDTHH:MM:SS), année {year} si absente ;
- "iban_origine" : compte de l'émetteur ;
- "iban_destinataire" : compte du destinataire ;
- "montant" : nombre sans devise ;
- "banque_source" : banque de l'émetteur, ou null si absente.

Texte : {text}
JSON :"""


def call_ollama(prompt: str) -> str:
    """Appelle un petit modèle local via l'API Ollama (sortie forcée en JSON)."""
    body = json.dumps({
        "model": OLLAMA_MODEL, "prompt": prompt, "stream": False,
        "format": "json", "options": {"temperature": 0},
    }).encode()
    request = urllib.request.Request(
        f"{OLLAMA_URL}/api/generate", data=body, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return json.loads(response.read())["response"]
    except (urllib.error.URLError, TimeoutError) as exc:
        raise TransientError(f"SLM injoignable : {exc}") from exc


def extract_transaction_from_text(
    text: str, llm: Callable[[str], str] = call_ollama, default_year: int | None = None
) -> TransactionRow:
    """Texte brut -> transaction validée. Aucune valeur inventée : si ça manque, on échoue."""
    year = default_year or datetime.now().year
    answer = llm(PROMPT.format(text=text.strip(), year=year))
    try:
        data = json.loads(answer)
        iban_src = str(data["iban_origine"]).replace(" ", "").upper()
        iban_dst = str(data["iban_destinataire"]).replace(" ", "").upper()
        return TransactionRow(
            datetime_transaction=data["datetime_transaction"],
            iban_origine=iban_src, pays_source=iban_src[:2],
            banque_source=data.get("banque_source") or "INCONNUE",
            iban_destinataire=iban_dst, pays_destinataire=iban_dst[:2],
            montant=str(data["montant"]),
        )
    except (json.JSONDecodeError, KeyError, TypeError, PydanticValidationError) as exc:
        raise InvalidDataError(f"Extraction SLM invalide ({exc}) pour : {text!r}") from exc


def to_csv_content(row: TransactionRow) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=COLUMNS)
    writer.writeheader()
    writer.writerow({**row.model_dump(), "montant": f"{row.montant:.2f}"})
    return buffer.getvalue()


def ingest_text(text: str, llm: Callable[[str], str] = call_ollama) -> bool:
    """Texte -> SLM -> CSV -> MÊME flux que les fichiers. True = inséré, False = déjà traité."""
    content = to_csv_content(extract_transaction_from_text(text, llm))
    name = f"text_{compute_hash(content)[:12]}.csv"
    return process_and_load_content(name, content)
