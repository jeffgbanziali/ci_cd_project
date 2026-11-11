"""Valeurs attendues, calculées À PART à partir du jeu de données déterministe
(src/pipeline/generator.py : 3 fichiers, 17 transactions, 6 > 5000)."""
from decimal import Decimal

TOTAL_TRANSACTIONS = 17
TOTAL_FLAGGED = 6
FILE_COUNT = 3
ROWS_PER_FILE = {
    "transactions_batch_1.csv": 6,
    "transactions_batch_2.csv": 5,
    "transactions_batch_3.csv": 6,
}

SENT_BY_IBAN = {
    "DE89370400440532013000": Decimal("20001.01"),
    "ES9121000418450200051332": Decimal("10800.75"),
    "FR1420041010050500013M02606": Decimal("11450.00"),
    "FR7630004000031234567890143": Decimal("12320.49"),
    "GB29NWBK60161331926819": Decimal("20000.00"),
}
SENT_BY_BANK = {
    "BNP Paribas": Decimal("12320.49"),
    "Banco Santander": Decimal("10800.75"),
    "Deutsche Bank": Decimal("20001.01"),
    "NatWest": Decimal("20000.00"),
    "Societe Generale": Decimal("11450.00"),
}
RECEIVED_BY_IBAN = {
    "DE89370400440532013000": Decimal("4251.25"),
    "ES9121000418450200051332": Decimal("21199.99"),
    "FR1420041010050500013M02606": Decimal("29000.00"),
    "FR7630004000031234567890143": Decimal("15100.01"),
    "GB29NWBK60161331926819": Decimal("5021.00"),
}

# Frontière du flag : STRICTEMENT supérieur à 5000
FLAG_EXPECTATIONS = {
    Decimal("4999.99"): False,
    Decimal("5000.00"): False,
    Decimal("5000.01"): True,
    Decimal("5001.00"): True,
}
