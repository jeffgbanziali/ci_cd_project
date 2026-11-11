import copy

import pandas as pd

from src.pipeline.transformer import (
    flag_high_value_transactions, process_all, sum_amount_by_banque_source,
    sum_amount_by_iban_destinataire, sum_amount_by_iban_origine,
)


def make_df():
    return pd.DataFrame({
        "iban_origine": ["A", "A", "B"],
        "banque_source": ["BANK_1", "BANK_1", "BANK_2"],
        "iban_destinataire": ["X", "Y", "X"],
        "montant": [100.0, 200.0, 50.0],
    })


def test_aggregations_values():
    df = make_df()
    orig = sum_amount_by_iban_origine(df).set_index("iban_origine")["total_envoye"]
    assert orig.to_dict() == {"A": 300.0, "B": 50.0}
    bank = sum_amount_by_banque_source(df).set_index("banque_source")["total_envoye"]
    assert bank.to_dict() == {"BANK_1": 300.0, "BANK_2": 50.0}
    dest = sum_amount_by_iban_destinataire(df).set_index("iban_destinataire")["total_recu"]
    assert dest.to_dict() == {"X": 150.0, "Y": 200.0}


def test_flag_boundary_is_strictly_greater_than_5000():
    df = pd.DataFrame({"montant": [4999.99, 5000.00, 5000.01, 5001.00]})
    flags = flag_high_value_transactions(df)["is_high_value"].tolist()
    assert flags == [False, False, True, True]


def test_functions_are_pure_input_not_modified():
    df = make_df()
    snapshot = df.copy(deep=True)
    flag_high_value_transactions(df)
    sum_amount_by_iban_origine(df)
    sum_amount_by_banque_source(df)
    sum_amount_by_iban_destinataire(df)
    process_all(df)
    pd.testing.assert_frame_equal(df, snapshot)
    assert "is_high_value" not in df.columns


def test_functions_are_deterministic():
    df = make_df()
    first, second = process_all(copy.deepcopy(df)), process_all(copy.deepcopy(df))
    pd.testing.assert_frame_equal(first.transactions, second.transactions)
    pd.testing.assert_frame_equal(first.by_iban_origine, second.by_iban_origine)
