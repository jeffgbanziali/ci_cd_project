"""Traitements métier : FONCTIONS PURES (ne modifient pas leur entrée)."""
from dataclasses import dataclass

import pandas as pd


def flag_high_value_transactions(df: pd.DataFrame, threshold: float = 5000.0) -> pd.DataFrame:
    """Ajoute is_high_value (montant STRICTEMENT > seuil) sans muter df."""
    res = df.copy()
    res["montant"] = pd.to_numeric(res["montant"])
    res["is_high_value"] = res["montant"] >= threshold
    return res


def _sum_by(df: pd.DataFrame, key: str, out_name: str) -> pd.DataFrame:
    res = df.copy()
    res["montant"] = pd.to_numeric(res["montant"])
    grouped = res.groupby(key, as_index=False)["montant"].sum()
    grouped["montant"] = grouped["montant"].round(2)
    return grouped.rename(columns={"montant": out_name})


def sum_amount_by_iban_origine(df: pd.DataFrame) -> pd.DataFrame:
    return _sum_by(df, "iban_origine", "total_envoye")


def sum_amount_by_banque_source(df: pd.DataFrame) -> pd.DataFrame:
    return _sum_by(df, "banque_source", "total_envoye")


def sum_amount_by_iban_destinataire(df: pd.DataFrame) -> pd.DataFrame:
    return _sum_by(df, "iban_destinataire", "total_recu")


@dataclass(frozen=True)
class ProcessedResult:
    transactions: pd.DataFrame
    by_iban_origine: pd.DataFrame
    by_banque_source: pd.DataFrame
    by_iban_destinataire: pd.DataFrame


def process_all(df: pd.DataFrame) -> ProcessedResult:
    """Applique tous les traitements (pur : df n'est pas modifié)."""
    return ProcessedResult(
        transactions=flag_high_value_transactions(df),
        by_iban_origine=sum_amount_by_iban_origine(df),
        by_banque_source=sum_amount_by_banque_source(df),
        by_iban_destinataire=sum_amount_by_iban_destinataire(df),
    )
