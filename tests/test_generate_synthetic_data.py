"""Validation tests for generate_synthetic_data.py output.

Mirrors the V1–V7 checks from the Step 1.2 plan:
  V1  VBAP.VBELN        → VBAK
  V2  LIPS.VGBEL        → VBAK
  V3  EKPO.EBELN        → EKKO
  V4  VBAP.MATNR        → MARA
  V5  MSEG.(MBLNR,MJAHR)→ MKPF
  V6  No NULL in PK fields
  V7  DATS fields parseable as YYYYMMDD

Extended:
  LIPS.VBELN   → LIKP
  EKET.(EBELN,EBELP) → EKPO
  VBBE.VBELN   → VBAK
  EKPO.MATNR   → MARA
  No duplicate PKs for key tables
"""

from pathlib import Path

import pandas as pd
import pytest

BASE = Path("data/raw/se16")
SUFFIX = "_20241231.csv"


def load(table: str) -> pd.DataFrame:
    path = BASE / table / f"{table}{SUFFIX}"
    if not path.exists():
        pytest.skip(f"CSV not found: {path}. Run scripts/generate_synthetic_data.py first.")
    return pd.read_csv(path, dtype=str)


@pytest.fixture(scope="session")
def tables():
    return {
        t: load(t)
        for t in [
            "VBAK",
            "VBAP",
            "LIKP",
            "LIPS",
            "VBUP",
            "VBBE",
            "EKKO",
            "EKPO",
            "EKET",
            "MKPF",
            "MSEG",
            "RESB",
            "MARA",
            "MARC",
            "MARD",
            "T001W",
            "KNA1",
            "LFA1",
        ]
    }


# ─── V1–V5 + extended: FK integrity ──────────────────────────────────────────
# Use isin() so a missing FK gives a real failure (not a false positive).


def test_v1_vbap_vbeln_in_vbak(tables):
    missing = ~tables["VBAP"]["VBELN"].isin(set(tables["VBAK"]["VBELN"]))
    assert not missing.any(), f"VBAP: {missing.sum()} rows with VBELN not in VBAK"


def test_v2_lips_vgbel_in_vbak(tables):
    missing = ~tables["LIPS"]["VGBEL"].isin(set(tables["VBAK"]["VBELN"]))
    assert not missing.any(), f"LIPS: {missing.sum()} rows with VGBEL not in VBAK"


def test_v3_ekpo_ebeln_in_ekko(tables):
    missing = ~tables["EKPO"]["EBELN"].isin(set(tables["EKKO"]["EBELN"]))
    assert not missing.any(), f"EKPO: {missing.sum()} rows with EBELN not in EKKO"


def test_v4_vbap_matnr_in_mara(tables):
    missing = ~tables["VBAP"]["MATNR"].isin(set(tables["MARA"]["MATNR"]))
    assert not missing.any(), f"VBAP: {missing.sum()} rows with MATNR not in MARA"


def test_v5_mseg_mblnr_in_mkpf(tables):
    mkpf_keys = set(zip(tables["MKPF"]["MBLNR"], tables["MKPF"]["MJAHR"], strict=False))
    mseg_keys = zip(tables["MSEG"]["MBLNR"], tables["MSEG"]["MJAHR"], strict=False)
    missing = sum(1 for k in mseg_keys if k not in mkpf_keys)
    assert missing == 0, f"MSEG: {missing} rows with (MBLNR, MJAHR) not in MKPF"


def test_lips_vbeln_in_likp(tables):
    missing = ~tables["LIPS"]["VBELN"].isin(set(tables["LIKP"]["VBELN"]))
    assert not missing.any(), f"LIPS: {missing.sum()} rows with VBELN not in LIKP"


def test_eket_key_in_ekpo(tables):
    ekpo_keys = set(zip(tables["EKPO"]["EBELN"], tables["EKPO"]["EBELP"], strict=False))
    eket_keys = zip(tables["EKET"]["EBELN"], tables["EKET"]["EBELP"], strict=False)
    missing = sum(1 for k in eket_keys if k not in ekpo_keys)
    assert missing == 0, f"EKET: {missing} rows with (EBELN, EBELP) not in EKPO"


def test_vbbe_vbeln_in_vbak(tables):
    missing = ~tables["VBBE"]["VBELN"].isin(set(tables["VBAK"]["VBELN"]))
    assert not missing.any(), f"VBBE: {missing.sum()} rows with VBELN not in VBAK"


def test_ekpo_matnr_in_mara(tables):
    missing = ~tables["EKPO"]["MATNR"].isin(set(tables["MARA"]["MATNR"]))
    assert not missing.any(), f"EKPO: {missing.sum()} rows with MATNR not in MARA"


# ─── V6: No NULL in PK fields ────────────────────────────────────────────────


@pytest.mark.parametrize(
    "table,pk_cols",
    [
        ("VBAK", ["VBELN"]),
        ("VBAP", ["VBELN", "POSNR"]),
        ("LIKP", ["VBELN"]),
        ("LIPS", ["VBELN", "POSNR"]),
        ("VBUP", ["VBELN", "POSNR"]),
        ("EKKO", ["EBELN"]),
        ("EKPO", ["EBELN", "EBELP"]),
        ("EKET", ["EBELN", "EBELP"]),
        ("MKPF", ["MBLNR", "MJAHR"]),
        ("MSEG", ["MBLNR", "MJAHR", "ZEILE"]),
        ("MARA", ["MATNR"]),
        ("MARC", ["MATNR", "WERKS"]),
        ("MARD", ["MATNR", "WERKS", "LGORT"]),
        ("T001W", ["WERKS"]),
        ("KNA1", ["KUNNR"]),
        ("LFA1", ["LIFNR"]),
    ],
)
def test_v6_pk_not_null(tables, table, pk_cols):
    null_count = tables[table][pk_cols].isnull().sum().sum()
    assert null_count == 0, f"{table}: NULL found in PK columns {pk_cols}"


# ─── V7: DATS format = YYYYMMDD ──────────────────────────────────────────────


@pytest.mark.parametrize(
    "table,col",
    [
        ("VBAK", "ERDAT"),
        ("LIKP", "BLDAT"),
        ("LIKP", "WADAT"),
        ("EKKO", "BEDAT"),
        ("MKPF", "BUDAT"),
        ("MARA", "ERSDA"),
    ],
)
def test_v7_dats_format(tables, table, col):
    series = tables[table][col].dropna().replace("", pd.NA).dropna()
    try:
        pd.to_datetime(series, format="%Y%m%d")
    except Exception as exc:
        pytest.fail(f"{table}.{col} contains invalid YYYYMMDD values: {exc}")


# ─── No duplicate PKs ─────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "table,pk_cols",
    [
        ("VBAK", ["VBELN"]),
        ("VBAP", ["VBELN", "POSNR"]),
        ("LIKP", ["VBELN"]),
        ("EKKO", ["EBELN"]),
        ("EKPO", ["EBELN", "EBELP"]),
        ("EKET", ["EBELN", "EBELP", "ETENR"]),
        ("MARA", ["MATNR"]),
        ("MARC", ["MATNR", "WERKS"]),
        ("MARD", ["MATNR", "WERKS", "LGORT"]),
        ("T001W", ["WERKS"]),
    ],
)
def test_no_duplicate_pk(tables, table, pk_cols):
    dupes = tables[table].duplicated(subset=pk_cols).sum()
    assert dupes == 0, f"{table}: {dupes} duplicate rows on PK {pk_cols}"


# ─── SAP field format checks ─────────────────────────────────────────────────


def test_matnr_18_chars(tables):
    lengths = tables["MARA"]["MATNR"].str.len()
    assert (lengths == 18).all(), "MARA.MATNR must be exactly 18 chars"


def test_vbeln_10_chars(tables):
    for tbl in ("VBAK", "LIKP"):
        lengths = tables[tbl]["VBELN"].str.len()
        assert (lengths == 10).all(), f"{tbl}.VBELN must be exactly 10 chars"


def test_kunnr_10_chars(tables):
    lengths = tables["KNA1"]["KUNNR"].str.len()
    assert (lengths == 10).all(), "KNA1.KUNNR must be exactly 10 chars"


def test_lifnr_10_chars(tables):
    lengths = tables["LFA1"]["LIFNR"].str.len()
    assert (lengths == 10).all(), "LFA1.LIFNR must be exactly 10 chars"


def test_mandt_is_100(tables):
    for tbl in ("VBAK", "EKKO", "MARA"):
        assert (tables[tbl]["MANDT"] == "100").all(), f"{tbl}.MANDT must all be '100'"


# ─── Volume sanity checks ─────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "table,min_rows",
    [
        ("VBAK", 5000),
        ("VBAP", 20000),
        ("LIKP", 4000),
        ("EKKO", 1500),
        ("EKPO", 4000),
        ("MARA", 500),
        ("KNA1", 100),
        ("LFA1", 50),
    ],
)
def test_volume_min(tables, table, min_rows):
    assert (
        len(tables[table]) >= min_rows
    ), f"{table}: expected >= {min_rows} rows, got {len(tables[table])}"
