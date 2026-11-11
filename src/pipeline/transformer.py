import pandas as pd

def flag_high_value_transactions(df: pd.DataFrame, threshold: float = 5000.0) -> pd.DataFrame:
    """Fonction pure: ajoute une colonne is_high_value sans muter df."""
    res = df.copy()
    res["montant"] = pd.to_numeric(res["montant"])
    res["is_high_value"] = res["montant"] > threshold
    return res

def sum_amount_by_iban_origine(df: pd.DataFrame) -> pd.DataFrame:
    """Fonction pure: calcule la somme envoyée par iban_origine."""
    res = df.copy()
    res["montant"] = pd.to_numeric(res["montant"])
    return res.groupby("iban_origine", as_index=False)["montant"].sum().rename(columns={"montant": "total_envoye"})

def sum_amount_by_banque_source(df: pd.DataFrame) -> pd.DataFrame:
    """Fonction pure: calcule la somme envoyée par banque_source."""
    res = df.copy()
    res["montant"] = pd.to_numeric(res["montant"])
    return res.groupby("banque_source", as_index=False)["montant"].sum().rename(columns={"montant": "total_envoye"})

def sum_amount_by_iban_destinataire(df: pd.DataFrame) -> pd.DataFrame:
    """Fonction pure: calcule la somme reçue par iban_destinataire."""
    res = df.copy()
    res["montant"] = pd.to_numeric(res["montant"])
    return res.groupby("iban_destinataire", as_index=False)["montant"].sum().rename(columns={"montant": "total_recu"})