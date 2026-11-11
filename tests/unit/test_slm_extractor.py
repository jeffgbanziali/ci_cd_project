import json
from decimal import Decimal

import pytest

from src.errors import InvalidDataError
from src.pipeline.slm_extractor import extract_transaction_from_text, to_csv_content

TEXT = ("Le 12 septembre à 14h30, le compte FR761234567890 a envoyé 6200 € "
        "vers le compte DE987654321 appartenant à une banque allemande.")


def fake_llm(prompt: str) -> str:
    assert "FR761234567890" in prompt          # le texte est bien transmis au modèle
    return json.dumps({
        "datetime_transaction": "2026-09-12T14:30:00",
        "iban_origine": "FR761234567890", "iban_destinataire": "DE987654321",
        "montant": 6200, "banque_source": None,
    })


def test_extraction_from_text_with_example_sentence():
    row = extract_transaction_from_text(TEXT, llm=fake_llm)
    assert row.iban_origine == "FR761234567890" and row.pays_source == "FR"
    assert row.iban_destinataire == "DE987654321" and row.pays_destinataire == "DE"
    assert row.montant == Decimal("6200") and row.banque_source == "INCONNUE"
    assert "6200.00" in to_csv_content(row)


@pytest.mark.parametrize("answer", ["pas du json", json.dumps({"montant": 10}),
                                    json.dumps({"datetime_transaction": "2026-09-12T14:30:00",
                                                "iban_origine": "FR761234567890",
                                                "iban_destinataire": "DE987654321",
                                                "montant": -3})])
def test_bad_model_output_is_rejected_nothing_invented(answer):
    with pytest.raises(InvalidDataError):
        extract_transaction_from_text(TEXT, llm=lambda _p: answer)
