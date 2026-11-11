import pytest

from src.errors import InvalidDataError
from src.pipeline.generator import BATCHES, COLUMNS, build_rows
from src.pipeline.loader import parse_and_validate

HEADER = ",".join(COLUMNS)
VALID_LINE = "2026-01-15 10:00:00,FR7630004000031234567890143,FR,BNP,DE89370400440532013000,DE,6200.00"


def test_valid_csv_is_parsed():
    df = parse_and_validate(f"{HEADER}\n{VALID_LINE}\n")
    assert len(df) == 1 and df.loc[0, "montant"] == 6200.0


def test_missing_column_is_rejected():
    bad_header = HEADER.replace(",montant", "")
    with pytest.raises(InvalidDataError, match="montant"):
        parse_and_validate(f"{bad_header}\n2026-01-15 10:00:00,FR76,FR,BNP,DE89,DE\n")


@pytest.mark.parametrize("bad_line, expected_field", [
    ("2026-01-15 10:00:00,FR7630004000031234567890143,FR,BNP,DE89370400440532013000,DE,abc", "montant"),
    ("2026-01-15 10:00:00,FR7630004000031234567890143,FR,BNP,DE89370400440532013000,DE,-5", "montant"),
    ("not-a-date,FR7630004000031234567890143,FR,BNP,DE89370400440532013000,DE,10", "datetime"),
    ("2026-01-15 10:00:00,XX,FR,BNP,DE89370400440532013000,DE,10", "iban_origine"),
])
def test_invalid_rows_are_rejected_with_line_number(bad_line, expected_field):
    with pytest.raises(InvalidDataError, match=f"ligne 2.*{expected_field}"):
        parse_and_validate(f"{HEADER}\n{bad_line}\n")


def test_empty_file_is_rejected():
    with pytest.raises(InvalidDataError):
        parse_and_validate("")
    with pytest.raises(InvalidDataError, match="aucune transaction"):
        parse_and_validate(f"{HEADER}\n")


def test_generated_files_have_5_to_10_rows_and_are_deterministic():
    for name in BATCHES:
        assert 5 <= len(build_rows(name)) <= 10
        assert build_rows(name) == build_rows(name)


def test_written_csv_files_match_the_required_format(tmp_path):
    """Le sujet impose : plusieurs fichiers, 5 à 10 transactions chacun, 7 colonnes exactes."""
    import csv

    from src.pipeline.generator import generate_csv_files

    paths = generate_csv_files(str(tmp_path), num_files=3)
    assert len(paths) >= 2                                   # « plusieurs fichiers »
    for path in paths:
        with open(path, newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            rows = list(reader)
        assert reader.fieldnames == COLUMNS == [
            "datetime_transaction", "iban_origine", "pays_source", "banque_source",
            "iban_destinataire", "pays_destinataire", "montant",
        ]
        assert 5 <= len(rows) <= 10
        for row in rows:                                     # pays cohérent avec l'IBAN
            assert row["iban_origine"][:2] == row["pays_source"]
            assert row["iban_destinataire"][:2] == row["pays_destinataire"]
            assert row["iban_origine"] != row["iban_destinataire"]
