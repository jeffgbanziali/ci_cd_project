"""Génération de CSV DÉTERMINISTES : les valeurs attendues sont connues d'avance.

Cas volontairement couverts pour tester chaque traitement :
  - montants 4999.99 / 5000.00 / 5000.01 / 5001.00 : frontière du flag (> 5000 strict) ;
  - plusieurs transactions par émetteur : sommes par IBAN et par banque ;
  - un IBAN à la fois émetteur et destinataire ;
  - plusieurs banques et pays.
"""
import csv
import os

COLUMNS = [
    "datetime_transaction", "iban_origine", "pays_source", "banque_source",
    "iban_destinataire", "pays_destinataire", "montant",
]

A = ("FR7630004000031234567890143", "FR", "BNP Paribas")
B = ("FR1420041010050500013M02606", "FR", "Societe Generale")
C = ("DE89370400440532013000", "DE", "Deutsche Bank")
D = ("ES9121000418450200051332", "ES", "Banco Santander")
E = ("GB29NWBK60161331926819", "GB", "NatWest")

# (datetime, émetteur, destinataire, montant)
BATCHES = {
    "transactions_batch_1.csv": [
        ("2026-01-05 09:15:00", A, B, "1200.00"),
        ("2026-01-05 10:30:00", A, C, "800.50"),
        ("2026-01-05 11:45:00", B, A, "5000.00"),   # frontière : PAS de flag
        ("2026-01-05 14:00:00", C, A, "5000.01"),   # flag
        ("2026-01-05 16:20:00", D, B, "7500.00"),   # flag
        ("2026-01-05 18:05:00", A, D, "4999.99"),
    ],
    "transactions_batch_2.csv": [
        ("2026-01-06 08:00:00", B, C, "250.00"),
        ("2026-01-06 09:30:00", A, B, "300.00"),
        ("2026-01-06 12:10:00", C, D, "10000.00"),  # flag
        ("2026-01-06 15:45:00", D, A, "100.00"),
        ("2026-01-06 17:30:00", B, D, "6200.00"),   # flag
    ],
    "transactions_batch_3.csv": [
        ("2026-01-07 09:00:00", E, A, "5000.00"),
        ("2026-01-07 10:10:00", E, B, "15000.00"),  # flag
        ("2026-01-07 11:25:00", A, E, "20.00"),
        ("2026-01-07 13:40:00", D, C, "3200.75"),
        ("2026-01-07 16:00:00", A, B, "5000.00"),
        ("2026-01-07 19:30:00", C, E, "5001.00"),   # flag
    ],
}


def build_rows(filename: str) -> list[dict]:
    return [
        {
            "datetime_transaction": dt,
            "iban_origine": src[0], "pays_source": src[1], "banque_source": src[2],
            "iban_destinataire": dst[0], "pays_destinataire": dst[1],
            "montant": amount,
        }
        for dt, src, dst, amount in BATCHES[filename]
    ]


def generate_csv_files(output_dir: str = "data_generated", num_files: int = 3) -> list[str]:
    """Écrit `num_files` (1 à 3) fichiers CSV de 5 à 10 transactions. Retourne leurs chemins."""
    os.makedirs(output_dir, exist_ok=True)
    paths = []
    for name in list(BATCHES)[:num_files]:
        path = os.path.join(output_dir, name)
        with open(path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=COLUMNS)
            writer.writeheader()
            writer.writerows(build_rows(name))
        paths.append(path)
    return paths
