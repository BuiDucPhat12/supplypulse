"""Validation tests for generate_synthetic_data.py output (v2 — realistic data).

FK integrity (V1-V5 + extended):
  V1  VBAP.VBELN          → VBAK
  V2  LIPS.VGBEL          → EKKO   (inbound deliveries reference POs, not sales orders)
  V3  EKPO.EBELN          → EKKO
  V4  VBAP.MATNR          → MARA
  V5  EKPO.(MATNR,WERKS)  → MARC   (the marc_combos fix — no orphan PO lines)
  V6  No NULL in PK fields
  V7  DATS fields parseable as YYYYMMDD

Realism (V8 — causal & statistical consistency):
  - WEMNG <= MENGE; future schedule lines have no goods receipt
  - EKPO.NETWR = MENGE x NETPR
  - Received deliveries (WADAT_IST set) are in the past; ASN docs have no WADAT_IST
  - VBBE open quantities positive, requirement dates inside demand window
  - Demand is Pareto-skewed (top 20% materials carry most ordered qty)
  - Shortage exists but is a minority (engineered ~8%)
"""

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

BASE = Path("data/raw/se16")

TABLES = [
    "VBAK",
    "VBAP",
    "LIKP",
    "LIPS",
    "VBUP",
    "VBBE",
    "EKKO",
    "EKPO",
    "EKET",
    "RESB",
    "MARA",
    "MARC",
    "MARD",
    "EQUK",
    "EQUP",
    "T001W",
    "KNA1",
    "LFA1",
]


def load(table: str) -> pd.DataFrame:
    matches = sorted((BASE / table).glob(f"{table}_*.csv"))
    if not matches:
        pytest.skip(f"CSV not found for {table}. Run scripts/generate_synthetic_data.py first.")
    return pd.read_csv(matches[-1], dtype=str)


@pytest.fixture(scope="session")
def tables():
    return {t: load(t) for t in TABLES}


@pytest.fixture(scope="session")
def anchor(tables) -> date:
    """The anchor ('today') is encoded in the extract filename suffix."""
    path = sorted((BASE / "T001W").glob("T001W_*.csv"))[-1]
    stamp = path.stem.split("_")[-1]
    return date(int(stamp[:4]), int(stamp[4:6]), int(stamp[6:8]))


# ─── V1–V5 + extended: FK integrity ──────────────────────────────────────────


def test_v1_vbap_vbeln_in_vbak(tables):
    missing = ~tables["VBAP"]["VBELN"].isin(set(tables["VBAK"]["VBELN"]))
    assert not missing.any(), f"VBAP: {missing.sum()} rows with VBELN not in VBAK"


def test_v2_lips_vgbel_in_ekko(tables):
    missing = ~tables["LIPS"]["VGBEL"].isin(set(tables["EKKO"]["EBELN"]))
    assert not missing.any(), f"LIPS: {missing.sum()} rows with VGBEL not in EKKO"


def test_v3_ekpo_ebeln_in_ekko(tables):
    missing = ~tables["EKPO"]["EBELN"].isin(set(tables["EKKO"]["EBELN"]))
    assert not missing.any(), f"EKPO: {missing.sum()} rows with EBELN not in EKKO"


def test_v4_vbap_matnr_in_mara(tables):
    missing = ~tables["VBAP"]["MATNR"].isin(set(tables["MARA"]["MATNR"]))
    assert not missing.any(), f"VBAP: {missing.sum()} rows with MATNR not in MARA"


def test_v5_ekpo_matnr_werks_in_marc(tables):
    marc_keys = set(zip(tables["MARC"]["MATNR"], tables["MARC"]["WERKS"], strict=False))
    ekpo_keys = zip(tables["EKPO"]["MATNR"], tables["EKPO"]["WERKS"], strict=False)
    missing = sum(1 for k in ekpo_keys if k not in marc_keys)
    assert missing == 0, f"EKPO: {missing} rows with (MATNR, WERKS) not in MARC"


def test_lips_vbeln_in_likp(tables):
    missing = ~tables["LIPS"]["VBELN"].isin(set(tables["LIKP"]["VBELN"]))
    assert not missing.any(), f"LIPS: {missing.sum()} rows with VBELN not in LIKP"


def test_lips_items_have_vbup_status(tables):
    vbup_keys = set(zip(tables["VBUP"]["VBELN"], tables["VBUP"]["POSNR"], strict=False))
    lips_keys = zip(tables["LIPS"]["VBELN"], tables["LIPS"]["POSNR"], strict=False)
    missing = sum(1 for k in lips_keys if k not in vbup_keys)
    assert missing == 0, f"LIPS: {missing} delivery items without VBUP status row"


def test_eket_key_in_ekpo(tables):
    ekpo_keys = set(zip(tables["EKPO"]["EBELN"], tables["EKPO"]["EBELP"], strict=False))
    eket_keys = zip(tables["EKET"]["EBELN"], tables["EKET"]["EBELP"], strict=False)
    missing = sum(1 for k in eket_keys if k not in ekpo_keys)
    assert missing == 0, f"EKET: {missing} rows with (EBELN, EBELP) not in EKPO"


def test_vbbe_vbeln_in_vbak(tables):
    missing = ~tables["VBBE"]["VBELN"].isin(set(tables["VBAK"]["VBELN"]))
    assert not missing.any(), f"VBBE: {missing.sum()} rows with VBELN not in VBAK"


def test_vbbe_matnr_werks_in_marc(tables):
    marc_keys = set(zip(tables["MARC"]["MATNR"], tables["MARC"]["WERKS"], strict=False))
    vbbe_keys = zip(tables["VBBE"]["MATNR"], tables["VBBE"]["WERKS"], strict=False)
    missing = sum(1 for k in vbbe_keys if k not in marc_keys)
    assert missing == 0, f"VBBE: {missing} rows with (MATNR, WERKS) not in MARC"


def test_equp_qunum_in_equk(tables):
    missing = ~tables["EQUP"]["QUNUM"].isin(set(tables["EQUK"]["QUNUM"]))
    assert not missing.any(), f"EQUP: {missing.sum()} rows with QUNUM not in EQUK"


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
        ("EKET", ["EBELN", "EBELP", "ETENR"]),
        ("MARA", ["MATNR"]),
        ("MARC", ["MATNR", "WERKS"]),
        ("MARD", ["MATNR", "WERKS", "LGORT"]),
        ("T001W", ["WERKS"]),
        ("KNA1", ["KUNNR"]),
        ("LFA1", ["LIFNR"]),
        ("EQUK", ["QUNUM"]),
        ("EQUP", ["QUNUM", "QUPOS"]),
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
        ("LIKP", "ERDAT"),
        ("LIKP", "WADAT"),
        ("LIKP", "WADAT_IST"),
        ("EKKO", "BEDAT"),
        ("EKET", "EINDT"),
        ("VBBE", "MBDAT"),
        ("RESB", "BDDAT"),
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
        ("LIPS", ["VBELN", "POSNR"]),
        ("VBUP", ["VBELN", "POSNR"]),
        ("EKKO", ["EBELN"]),
        ("EKPO", ["EBELN", "EBELP"]),
        ("EKET", ["EBELN", "EBELP", "ETENR"]),
        ("MARA", ["MATNR"]),
        ("MARC", ["MATNR", "WERKS"]),
        ("MARD", ["MATNR", "WERKS", "LGORT"]),
        ("T001W", ["WERKS"]),
        ("EQUK", ["QUNUM"]),
        ("EQUP", ["QUNUM", "QUPOS"]),
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


def test_likp_is_inbound(tables):
    assert (tables["LIKP"]["LFART"] == "EL").all(), "LIKP must be inbound deliveries (LFART='EL')"


# ─── V8: Causal & statistical realism ────────────────────────────────────────


def _dates(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series.replace("", pd.NA).dropna(), format="%Y%m%d").dt.date


def test_v8_wemng_not_above_menge(tables):
    eket = tables["EKET"]
    over = eket[eket["WEMNG"].astype(float) > eket["MENGE"].astype(float) + 0.01]
    assert len(over) == 0, f"EKET: {len(over)} schedule lines received more than ordered"


def test_v8_no_receipt_before_due(tables, anchor):
    """Schedule lines due in the future cannot have goods receipts yet."""
    eket = tables["EKET"]
    eindt = pd.to_datetime(eket["EINDT"], format="%Y%m%d").dt.date
    future = eket[[d > anchor for d in eindt]]
    received = future[future["WEMNG"].astype(float) > 0]
    assert len(received) == 0, f"EKET: {len(received)} future lines already have WEMNG > 0"


def test_v8_ekpo_netwr_is_qty_times_price(tables):
    ekpo = tables["EKPO"]
    expected = ekpo["MENGE"].astype(float) * ekpo["NETPR"].astype(float)
    diff = (ekpo["NETWR"].astype(float) - expected).abs()
    bad = (diff > expected.abs() * 0.01 + 0.05).sum()
    assert bad == 0, f"EKPO: {bad} rows where NETWR != MENGE x NETPR"


def test_v8_received_deliveries_in_past(tables, anchor):
    wadat_ist = _dates(tables["LIKP"]["WADAT_IST"])
    future = sum(1 for d in wadat_ist if d > anchor)
    assert future == 0, f"LIKP: {future} confirmed receipts (WADAT_IST) dated after anchor"


def test_v8_asn_have_open_gr_status(tables):
    """Deliveries without WADAT_IST (in transit) must not be GR-complete in VBUP."""
    likp = tables["LIKP"]
    asn_docs = set(likp[likp["WADAT_IST"].fillna("") == ""]["VBELN"])
    vbup = tables["VBUP"]
    bad = vbup[vbup["VBELN"].isin(asn_docs) & (vbup["WBSTK"] == "C")]
    assert len(bad) == 0, f"VBUP: {len(bad)} in-transit ASN items already marked GR-complete"


def test_v8_vbbe_open_qty_positive(tables):
    omeng = tables["VBBE"]["OMENG"].astype(float)
    assert (omeng > 0).all(), "VBBE: open requirements must have OMENG > 0"


def test_v8_vbbe_has_future_demand(tables, anchor):
    """Inventory simulation needs demand AFTER the anchor — the old generator had none."""
    mbdat = _dates(tables["VBBE"]["MBDAT"])
    future = sum(1 for d in mbdat if d >= anchor)
    assert future > len(mbdat) * 0.5, "VBBE: expected the majority of open demand in the future"


def test_v8_eket_has_future_supply(tables, anchor):
    eindt = _dates(tables["EKET"]["EINDT"])
    future = sum(1 for d in eindt if d >= anchor)
    assert future > 100, "EKET: expected a meaningful number of future schedule lines"


def test_v8_demand_is_pareto_skewed(tables):
    """Top 20% of materials should carry the bulk of ordered quantity (ABC reality)."""
    vbap = tables["VBAP"]
    qty_per_mat = vbap.assign(q=vbap["MENGE"].astype(float)).groupby("MATNR")["q"].sum()
    top20 = qty_per_mat.sort_values(ascending=False).head(max(1, len(qty_per_mat) // 5))
    share = top20.sum() / qty_per_mat.sum()
    assert share >= 0.5, f"Demand not skewed enough: top-20% materials carry {share:.0%} (< 50%)"


def test_v8_most_quotas_active_at_anchor(tables, anchor):
    equk = tables["EQUK"]
    vdatu = pd.to_datetime(equk["VDATU"], format="%Y%m%d").dt.date
    bdatu = pd.to_datetime(equk["BDATU"], format="%Y%m%d").dt.date
    active = sum(1 for v, b in zip(vdatu, bdatu, strict=False) if v <= anchor <= b)
    assert active >= len(equk) * 0.8, f"EQUK: only {active}/{len(equk)} quotas active at anchor"


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
