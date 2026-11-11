"""CHARGEMENT et VALIDATION des données (aucun traitement métier ici)."""
import io
import logging
from datetime import datetime
from decimal import Decimal

import pandas as pd
from pydantic import BaseModel, Field
from pydantic import ValidationError as PydanticValidationError

from src.errors import InvalidDataError

logger = logging.getLogger(__name__)

COLUMNS = [
    "datetime_transaction", "iban_origine", "pays_source", "banque_source",
    "iban_destinataire", "pays_destinataire", "montant",
]
IBAN = r"^[A-Z]{2}\d{2}[A-Z0-9]{4,30}$"
COUNTRY = r"^[A-Z]{2}$"


class TransactionRow(BaseModel):
    """Format attendu d'une transaction (sert aussi à valider la sortie du SLM)."""

    datetime_transaction: datetime
    iban_origine: str = Field(pattern=IBAN)
    pays_source: str = Field(pattern=COUNTRY)
    banque_source: str = Field(min_length=1, max_length=100)
    iban_destinataire: str = Field(pattern=IBAN)
    pays_destinataire: str = Field(pattern=COUNTRY)
    montant: Decimal = Field(gt=0, max_digits=14, decimal_places=2)


def parse_and_validate(content: str, source: str = "<csv>") -> pd.DataFrame:
    """CSV (texte) -> DataFrame validé. Lève InvalidDataError si le format est incorrect."""
    try:
        raw = pd.read_csv(io.StringIO(content), dtype=str, keep_default_na=False)
    except (pd.errors.EmptyDataError, pd.errors.ParserError) as exc:
        raise InvalidDataError(f"{source} : CSV illisible ({exc})") from exc

    missing = [c for c in COLUMNS if c not in raw.columns]
    if missing:
        raise InvalidDataError(f"{source} : colonne(s) manquante(s) : {', '.join(missing)}")
    if raw.empty:
        raise InvalidDataError(f"{source} : fichier sans aucune transaction")

    rows = []
    for line, record in enumerate(raw[COLUMNS].to_dict("records"), start=2):
        try:
            row = TransactionRow(**record)
        except PydanticValidationError as exc:
            details = "; ".join(f"{e['loc'][0]}: {e['msg']}" for e in exc.errors())
            raise InvalidDataError(f"{source} ligne {line} : {details}") from exc
        data = row.model_dump()
        data["montant"] = float(row.montant)
        rows.append(data)
    return pd.DataFrame(rows, columns=COLUMNS)
