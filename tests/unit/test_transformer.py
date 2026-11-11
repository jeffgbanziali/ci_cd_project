import pandas as pd
from src.pipeline.transformer import (
    flag_high_value_transactions,
    sum_amount_by_iban_origine,
    sum_amount_by_banque_source,
    sum_amount_by_iban_destinataire
)

def test_pure_functions_immutability():
    df = pd.DataFrame({
        "datetime_transaction": ["2026-01-01 10:00:00"],
        "iban_origine": ["FR01"],
        "pays_source": ["FR"],
        "banque_source": ["BNP"],
        "iban_destinataire": ["DE02"],
        "pays_destinataire": ["DE"],
        "montant": [6000.0]
    })
    original_cols = list(df.columns)
    res = flag_high_value_transactions(df)
    
    # Vérification fonction pure : l'original n'a pas bougé
    assert list(df.columns) == original_cols
    assert res.loc[0, "is_high_value"] is True or res.loc[0, "is_high_value"] == 1

def test_aggregations():
    df = pd.DataFrame({
        "iban_origine": ["IBAN_A", "IBAN_A", "IBAN_B"],
        "banque_source": ["BANK_1", "BANK_1", "BANK_2"],
        "iban_destinataire": ["DEST_X", "DEST_Y", "DEST_X"],
        "montant": [100.0, 200.0, 50.0]
    })

    agg_orig = sum_amount_by_iban_origine(df)
    assert agg_orig[agg_orig["iban_origine"] == "IBAN_A"]["total_envoye"].iloc[0] == 300.0

    agg_bank = sum_amount_by_banque_source(df)
    assert agg_bank[agg_bank["banque_source"] == "BANK_1"]["total_envoye"].iloc[0] == 300.0

    agg_dest = sum_amount_by_iban_destinataire(df)
    assert agg_dest[agg_dest["iban_destinataire"] == "DEST_X"]["total_recu"].iloc[0] == 150.0