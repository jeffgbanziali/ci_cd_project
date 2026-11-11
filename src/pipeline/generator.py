import os
import random
from datetime import datetime, timedelta
import pandas as pd

IBANS_ORIGINE = [
    ("FR7630001007941234567890185", "FR", "BNP Paribas"),
    ("DE89370400440532013000", "DE", "Deutsche Bank"),
    ("ES9121000418450200051332", "ES", "Banco Santander")
]

IBANS_DEST = [
    ("FR7630004000031234567890143", "FR"),
    ("IT60X0542811101000000123456", "IT"),
    ("GB29NWBK60161331926819", "GB")
]

def generate_csv_files(output_dir: str = "data_generated", num_files: int = 3, seed: int = 42) -> list[str]:
    random.seed(seed)
    os.makedirs(output_dir, exist_ok=True)
    file_paths = []
    base_time = datetime(2026, 1, 15, 10, 0, 0)

    for i in range(num_files):
        rows = []
        count = random.randint(5, 10)
        for j in range(count):
            source = random.choice(IBANS_ORIGINE)
            dest = random.choice(IBANS_DEST)
            # Garantir au moins un montant > 5000 pour les tests du flag
            montant = round(6500.0 if (i == 0 and j == 0) else random.uniform(50.0, 7000.0), 2)
            trans_time = base_time + timedelta(minutes=random.randint(1, 1000))

            rows.append({
                "datetime_transaction": trans_time.strftime("%Y-%m-%d %H:%M:%S"),
                "iban_origine": source[0],
                "pays_source": source[1],
                "banque_source": source[2],
                "iban_destinataire": dest[0],
                "pays_destinataire": dest[1],
                "montant": montant
            })

        filepath = os.path.join(output_dir, f"transactions_batch_{i+1}.csv")
        pd.DataFrame(rows).to_csv(filepath, index=False)
        file_paths.append(filepath)

    return file_paths