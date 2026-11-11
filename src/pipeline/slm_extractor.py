import re
from datetime import datetime
from pydantic import BaseModel, Field

class ExtractedTransaction(BaseModel):
    datetime_transaction: datetime
    iban_origine: str
    pays_source: str
    banque_source: str
    iban_destinataire: str
    pays_destinataire: str
    montant: float = Field(gt=0)

def extract_transaction_from_text(text: str) -> ExtractedTransaction:
    """Simulateur/Parser SLM déterministe pour extraire les entités nommées du texte."""
    iban_pattern = r'[A-Z]{2}\d{2}[A-Z0-9]{4,30}'
    ibans = re.findall(iban_pattern, text)
    
    amount_match = re.search(r'(\d+(?:[\.,]\d+)?)\s*€', text)
    amount = float(amount_match.group(1).replace(',', '.')) if amount_match else 0.0

    iban_orig = ibans[0] if len(ibans) > 0 else "FR7600000000000000000000000"
    iban_dest = ibans[1] if len(ibans) > 1 else "DE000000000000000000000000"

    return ExtractedTransaction(
        datetime_transaction=datetime(2026, 9, 12, 14, 30, 0),
        iban_origine=iban_orig,
        pays_source=iban_orig[:2],
        banque_source="Banque Émettrice",
        iban_destinataire=iban_dest,
        pays_destinataire=iban_dest[:2],
        montant=amount
    )