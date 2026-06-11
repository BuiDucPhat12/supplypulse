"""Generate synthetic SAP ECC 6.0 CSV files mimicking SE16 extracts — v2 (realistic).

v2 redesign goals (see docs/notes/07_synthetic_data_v2_criteria.md):
  1. Anchor-relative dates: 24 months history + 6 months future around --anchor
     (default: today). Removes the hardcoded DATE '2024-09-01' workaround in dbt.
  2. Skewed distributions: ABC material classes, Zipf customer/vendor share,
     lognormal quantities — instead of uniform everything.
  3. Entity personas: each vendor has lead-time + OTD characteristics (incl. a few
     chronically late vendors); each material has a stable price and demand profile.
  4. Causal consistency: statuses derive from dates vs anchor, goods receipts only
     after due dates, NETWR = MENGE x NETPR, VBBE only for genuinely open items.
  5. Demand-supply balance with controlled anomalies: stock sized to demand,
     ~8% of material-plant combos engineered into shortage.
  6. LIKP/LIPS are INBOUND deliveries (ASN): LIPS.VGBEL -> EKKO.EBELN, matching
     how the dbt intermediate layer traces vendors (int_inbound_deliveries).
     VBUP carries GR status for delivery items ('C' = goods receipt complete).

Layer 0 -> 4 must run in order to preserve FK consistency.
Output: data/raw/se16/<TABLE>/<TABLE>_<ANCHOR:YYYYMMDD>.csv
"""

import argparse
import math
import random
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
from faker import Faker

fake = Faker("de_DE")
random.seed(42)
Faker.seed(42)

MANDT = "100"
OUT_DIR = Path("data/raw/se16")

# Set in main() from --anchor
ANCHOR: date = date.today()
HIST_START: date = ANCHOR - timedelta(days=730)
DEMAND_END: date = ANCHOR + timedelta(days=130)
SUPPLY_END: date = ANCHOR + timedelta(days=180)
SUFFIX: str = ""

N_MATERIALS = 500
N_CUSTOMERS = 100
N_VENDORS = 50
N_ORDERS = 6000
N_BAD_VENDORS = 3
SHORTAGE_RATIO = 0.08  # share of material-plant combos engineered into shortage

AUART_VALS = ["OR", "ZOR", "RE"]
BSART_VALS = ["NB", "FO", "UB"]
MTART_VALS = ["ROH", "FERT", "HALB", "HIBE"]
DISMM_VALS = ["PD", "VB", "ND"]
WAERS_VALS = ["EUR", "USD", "VND"]
MEINS_VALS = ["EA", "KG", "L", "M", "ST"]
INCO1_VALS = ["EXW", "DAP", "CIF", "DDP"]
BDART_VALS = ["KE", "KEL", "LSF"]
SAP_USERS = [f"USER{i:04d}" for i in range(1, 51)]
REGION_CODES = ["BW", "BY", "BE", "SN", "HH", "HE", "NW", "RP"]


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _fmt(d: date) -> str:
    return d.strftime("%Y%m%d")


def _pad(n: int, w: int = 10) -> str:
    return str(n).zfill(w)


def _lognorm(mean: float, sigma: float, lo: float, hi: float) -> float:
    return round(min(max(random.lognormvariate(math.log(mean), sigma), lo), hi), 2)


def _is_wd(d: date) -> bool:
    return d.weekday() < 5


def _next_wd(d: date) -> date:
    while not _is_wd(d):
        d += timedelta(days=1)
    return d


def _day_weight(d: date) -> float:
    """Trend x yearly seasonality x weekday pattern for business activity."""
    t = (d - HIST_START).days / max((ANCHOR - HIST_START).days, 1)
    trend = 1.0 + 0.25 * t
    doy = d.timetuple().tm_yday
    season = 1.0 + 0.18 * math.sin(2 * math.pi * (doy - 60) / 365.0)
    weekday = [1.10, 1.15, 1.10, 1.05, 0.90, 0.0, 0.0][d.weekday()]
    return trend * season * weekday


def _date_range(start: date, end: date) -> list[date]:
    return [start + timedelta(days=i) for i in range((end - start).days + 1)]


def _write(df: pd.DataFrame, table: str) -> None:
    p = OUT_DIR / table
    p.mkdir(parents=True, exist_ok=True)
    for old in p.glob(f"{table}_*.csv"):  # drop stale extracts so the loader sees one file
        old.unlink()
    df.to_csv(p / f"{table}{SUFFIX}", index=False, encoding="utf-8")
    print(f"  {table:10s}: {len(df):>7,} rows")


# ─── Layer 0 — Config ────────────────────────────────────────────────────────


def gen_t001w(ctx: dict) -> pd.DataFrame:
    plants = [
        ("1000", "Bosch Stuttgart", "BW", "Stuttgart", "01"),
        ("1001", "Bosch Munich", "BY", "Munich", "02"),
        ("1002", "Bosch Berlin", "BE", "Berlin", "03"),
        ("1003", "Bosch Leipzig", "SN", "Leipzig", "01"),
    ]
    rows = [
        {
            "MANDT": MANDT,
            "WERKS": w,
            "NAME1": name,
            "BWKEY": w,
            "LAND1": "DE",
            "REGIO": regio,
            "ORT01": ort,
            "FABKL": fabkl,
            "EKORG": "1000",
            "VKORG": "1000",
            "KUNNR": "",
            "LIFNR": "",
        }
        for w, name, regio, ort, fabkl in plants
    ]
    df = pd.DataFrame(rows)
    ctx["plant_ids"] = [p[0] for p in plants]
    ctx["calendar_ids"] = sorted({p[4] for p in plants})
    ctx["storage_locs"] = {w: ["0001", "0002", "0003"] for w in ctx["plant_ids"]}
    _write(df, "T001W")
    return df


def gen_tfact(ctx: dict) -> pd.DataFrame:
    cal_texts = {"01": "Standard DE Mon-Fri", "02": "Bavaria Mon-Sat", "03": "Berlin 24h"}
    rows = [
        {"MANDT": MANDT, "IDENT": cid, "SPRAS": lang, "LTEXT": cal_texts[cid]}
        for cid in ctx["calendar_ids"]
        for lang in ("E", "D")
    ]
    df = pd.DataFrame(rows)
    _write(df, "TFACT")
    return df


# ─── Layer 1 — Master data + personas ────────────────────────────────────────


def build_material_personas(ctx: dict) -> None:
    """ABC classes drive popularity, order-line size and stock policy."""
    personas: dict[str, dict] = {}
    classes = ["A"] * 50 + ["B"] * 100 + ["C"] * 350
    random.shuffle(classes)
    for i in range(1, N_MATERIALS + 1):
        matnr = _pad(i, 18)
        cls = classes[i - 1]
        if cls == "A":
            popularity = random.uniform(6.0, 12.0)
            base_qty = _lognorm(60, 0.5, 5, 2000)
        elif cls == "B":
            popularity = random.uniform(2.0, 5.0)
            base_qty = _lognorm(25, 0.5, 2, 800)
        else:
            popularity = random.uniform(0.3, 1.5)
            base_qty = _lognorm(8, 0.6, 1, 300)
        personas[matnr] = {
            "class": cls,
            "popularity": popularity,
            "base_qty": base_qty,
            "price": _lognorm(40, 1.0, 2, 3000),  # stable sales price per unit
        }
    ctx["mat_persona"] = personas
    ctx["material_ids"] = list(personas)
    ctx["mat_weights"] = [p["popularity"] for p in personas.values()]


def gen_mara(ctx: dict) -> pd.DataFrame:
    mat_groups = ["MG001", "MG002", "MG003", "MG004", "MG005"]
    rows = []
    material_uom: dict[str, str] = {}
    material_group: dict[str, str] = {}
    for matnr in ctx["material_ids"]:
        meins = random.choice(MEINS_VALS)
        matkl = random.choice(mat_groups)
        material_uom[matnr] = meins
        material_group[matnr] = matkl
        rows.append(
            {
                "MANDT": MANDT,
                "MATNR": matnr,
                "MTART": random.choice(MTART_VALS),
                "MBRSH": "M",
                "MATKL": matkl,
                "MEINS": meins,
                "BRGEW": _lognorm(5, 1.0, 0.1, 50),
                "GEWEI": "KG",
                "ERSDA": _fmt(HIST_START - timedelta(days=random.randint(180, 1500))),
            }
        )
    df = pd.DataFrame(rows)
    ctx["material_uom"] = material_uom
    ctx["material_group"] = material_group
    _write(df, "MARA")
    return df


def gen_kna1(ctx: dict) -> pd.DataFrame:
    rows = [
        {
            "MANDT": MANDT,
            "KUNNR": _pad(i, 10),
            "LAND1": random.choice(["DE", "AT", "CH", "FR", "PL"]),
            "NAME1": fake.company()[:35],
            "ORT01": fake.city()[:35],
            "PSTLZ": fake.postcode()[:10],
            "REGIO": random.choice(REGION_CODES),
            "KTOKD": "0001",
            "ERDAT": _fmt(HIST_START - timedelta(days=random.randint(90, 2000))),
        }
        for i in range(1, N_CUSTOMERS + 1)
    ]
    df = pd.DataFrame(rows)
    ctx["customer_ids"] = [r["KUNNR"] for r in rows]
    # Zipf-like share: a few key accounts drive most order volume
    ctx["customer_weights"] = [1.0 / (rank**0.9) for rank in range(1, N_CUSTOMERS + 1)]
    _write(df, "KNA1")
    return df


def gen_lfa1(ctx: dict) -> pd.DataFrame:
    personas: dict[str, dict] = {}
    bad_vendors = set(random.sample(range(1, N_VENDORS + 1), N_BAD_VENDORS))
    rows = []
    for i in range(1, N_VENDORS + 1):
        lifnr = _pad(i, 10)
        is_bad = i in bad_vendors
        personas[lifnr] = {
            "lt_mean": random.uniform(7, 40),  # purchase lead time (days)
            "lt_std": random.uniform(1, 4),
            "otd_rate": random.uniform(0.45, 0.62) if is_bad else random.uniform(0.86, 0.98),
            "late_extra": random.uniform(5, 20) if is_bad else random.uniform(2, 7),
            "share": 1.0 / (i**0.85),  # Zipf: top vendors win most quota
            "is_bad": is_bad,
        }
        rows.append(
            {
                "MANDT": MANDT,
                "LIFNR": lifnr,
                "LAND1": random.choice(["DE", "AT", "CH", "CN", "JP"]),
                "NAME1": fake.company()[:35],
                "ORT01": fake.city()[:35],
                "PSTLZ": fake.postcode()[:10],
                "REGIO": random.choice(REGION_CODES),
                "KTOKK": "0001",
                "STCD1": "",
                "ERDAT": _fmt(HIST_START - timedelta(days=random.randint(90, 2000))),
                "ERNAM": random.choice(SAP_USERS),
                "SPERR": "",
                "XCPDK": "",
            }
        )
    df = pd.DataFrame(rows)
    ctx["vendor_ids"] = [r["LIFNR"] for r in rows]
    ctx["vendor_persona"] = personas
    _write(df, "LFA1")
    return df


# ─── Layer 2 — Material-plant combos, quota arrangements ────────────────────


def build_marc_combos(ctx: dict) -> None:
    """Assign plants, procurement type and a vendor panel per material."""
    combos: list[tuple[str, str]] = []
    combo_info: dict[tuple[str, str], dict] = {}
    mat_vendors: dict[str, list[tuple[str, float]]] = {}
    vendor_ids = ctx["vendor_ids"]
    vendor_w = [ctx["vendor_persona"][v]["share"] for v in vendor_ids]
    for matnr in ctx["material_ids"]:
        n_vnd = random.choices([1, 2, 3], weights=[35, 45, 20])[0]
        panel: list[str] = []
        while len(panel) < n_vnd:
            v = random.choices(vendor_ids, weights=vendor_w)[0]
            if v not in panel:
                panel.append(v)
        shares = [random.uniform(0.5, 1.5) for _ in panel]
        total = sum(shares)
        mat_vendors[matnr] = [(v, s / total) for v, s in zip(panel, shares, strict=False)]

        n_plants = random.choices([1, 2, 3], weights=[40, 40, 20])[0]
        for werks in random.sample(ctx["plant_ids"], n_plants):
            combos.append((matnr, werks))
            combo_info[(matnr, werks)] = {
                "beskz": random.choices(["F", "E", "X"], weights=[85, 10, 5])[0],
            }
    ctx["marc_combos"] = combos
    ctx["combo_info"] = combo_info
    ctx["mat_vendors"] = mat_vendors
    ctx["mat_plants"] = {}
    for matnr, werks in combos:
        ctx["mat_plants"].setdefault(matnr, []).append(werks)
    ctx["shortage_combos"] = set(random.sample(combos, max(1, int(len(combos) * SHORTAGE_RATIO))))


def gen_equk_equp(ctx: dict) -> None:
    """Quota arrangements per externally procured material-plant; mostly valid
    around the anchor so int_equk_active (CURRENT_DATE check) finds them."""
    equk_rows, equp_rows = [], []
    qnum = 0
    quota_lookup: dict[tuple[str, str], list[tuple[str, float]]] = {}
    for matnr, werks in ctx["marc_combos"]:
        if ctx["combo_info"][(matnr, werks)]["beskz"] != "F":
            continue
        qnum += 1
        qunum = _pad(qnum, 10)
        if random.random() < 0.90:  # active window straddles the anchor
            vdatu = ANCHOR - timedelta(days=random.randint(60, 400))
            bdatu = ANCHOR + timedelta(days=random.randint(60, 365))
        else:  # a few expired arrangements for realism
            vdatu = ANCHOR - timedelta(days=random.randint(500, 800))
            bdatu = ANCHOR - timedelta(days=random.randint(10, 120))
        equk_rows.append(
            {
                "MANDT": MANDT,
                "MATNR": matnr,
                "WERKS": werks,
                "QUNUM": qunum,
                "VDATU": _fmt(vdatu),
                "BDATU": _fmt(bdatu),
                "SCMNG": _lognorm(50, 0.6, 1, 500),
                "ERDAT": _fmt(vdatu),
                "ERNAM": random.choice(SAP_USERS),
            }
        )
        quota_lookup[(matnr, werks)] = ctx["mat_vendors"][matnr]
        for pos, (lifnr, share) in enumerate(ctx["mat_vendors"][matnr], start=1):
            vp = ctx["vendor_persona"][lifnr]
            equp_rows.append(
                {
                    "MANDT": MANDT,
                    "QUNUM": qunum,
                    "QUPOS": _pad(pos, 3),
                    "BESKZ": "F",
                    "LIFNR": lifnr,
                    "BEWRK": werks,
                    "QUOTE": round(share * 100, 1),
                    "QUBMG": _lognorm(1000, 0.5, 100, 10000),
                    "QUMNG": _lognorm(200, 0.7, 0, 5000),
                    "MAXMG": _lognorm(5000, 0.4, 1000, 20000),
                    "MINLS": _lognorm(30, 0.5, 5, 200),
                    "MAXLS": _lognorm(400, 0.5, 50, 2000),
                    "PLIFZ": round(vp["lt_mean"]),
                    "PREIH": _pad(pos, 2),
                    "VERID": "",
                }
            )
    _write(pd.DataFrame(equk_rows), "EQUK")
    _write(pd.DataFrame(equp_rows), "EQUP")


# ─── Layer 3 — Transaction SD (sales demand) ─────────────────────────────────


def gen_sales(ctx: dict) -> None:
    """VBAK/VBAP with seasonal order dates; VBUP status + VBBE open requirements
    derived causally from requested date vs anchor."""
    hist_days = [d for d in _date_range(HIST_START, ANCHOR) if _is_wd(d)]
    hist_weights = [_day_weight(d) for d in hist_days]
    pstyv_vals = ["TAN", "TANN", "TATX"]

    vbak_rows, vbap_rows, vbbe_rows = [], [], []
    vbup_rows = ctx.setdefault("vbup_rows", [])
    demand = ctx.setdefault("demand", {})  # (matnr, werks) -> {"overdue": x, "future": y}

    for i in range(1, N_ORDERS + 1):
        vbeln = _pad(i, 10)
        kunnr = random.choices(ctx["customer_ids"], weights=ctx["customer_weights"])[0]
        erdat = random.choices(hist_days, weights=hist_weights)[0]
        waerk = random.choices(WAERS_VALS, weights=[80, 15, 5])[0]
        auart = random.choices(AUART_VALS, weights=[70, 25, 5])[0]
        n_items = random.choices([2, 3, 4, 5, 6, 7], weights=[20, 25, 22, 15, 10, 8])[0]

        order_netwr = 0.0
        item_statuses = []
        for pos in range(1, n_items + 1):
            posnr = _pad(pos * 10, 6)
            matnr = random.choices(ctx["material_ids"], weights=ctx["mat_weights"])[0]
            mp = ctx["mat_persona"][matnr]
            werks = random.choice(ctx["mat_plants"][matnr])
            lgort = random.choice(ctx["storage_locs"][werks])
            meins = ctx["material_uom"][matnr]
            qty = _lognorm(mp["base_qty"], 0.45, 1, 5000)
            netwr = round(qty * mp["price"] * random.uniform(0.97, 1.03), 2)
            order_netwr += netwr
            requested = _next_wd(
                min(
                    erdat + timedelta(days=max(3, round(random.lognormvariate(math.log(30), 0.9)))),
                    DEMAND_END,
                )
            )
            rejected = random.random() < 0.02

            # Causal status: old past-due orders are closed; recent past-due can be
            # stuck (-> overdue backlog); future requested dates stay open.
            if rejected or requested < ANCHOR - timedelta(days=90):
                status, open_qty = "C", 0.0
            elif requested < ANCHOR:
                if random.random() < 0.92:
                    status, open_qty = "C", 0.0
                else:  # stuck order -> overdue backlog
                    status = "B"
                    open_qty = round(qty * random.uniform(0.2, 1.0), 2)
            else:
                status, open_qty = "A", qty
            item_statuses.append(status)

            vbap_rows.append(
                {
                    "MANDT": MANDT,
                    "VBELN": vbeln,
                    "POSNR": posnr,
                    "MATNR": matnr,
                    "MATKL": ctx["material_group"][matnr],
                    "MENGE": qty,
                    "MEINS": meins,
                    "NETWR": netwr,
                    "WAERK": waerk,
                    "WERKS": werks,
                    "LGORT": lgort,
                    "PSTYV": random.choice(pstyv_vals),
                    "ABGRU": "01" if rejected else "",
                    "ERDAT": _fmt(erdat),
                }
            )
            vbup_rows.append(
                {
                    "MANDT": MANDT,
                    "VBELN": vbeln,
                    "POSNR": posnr,
                    "GBSTA": status,
                    "ABSTK": "",
                    "WBSTK": status,
                    "FKSTK": status,
                    "LVSTK": status,
                    "LSSTK": "",
                    "KOSTA": "",
                    "LFGSK": status,
                }
            )
            if open_qty > 0:
                vbbe_rows.append(
                    {
                        "MANDT": MANDT,
                        "VBELN": vbeln,
                        "POSNR": posnr,
                        "MATNR": matnr,
                        "WERKS": werks,
                        "MBDAT": _fmt(requested),
                        "OMENG": open_qty,
                        "VMENG": round(open_qty * random.uniform(0.85, 1.0), 2),
                        "MEINS": meins,
                        "BDART": random.choice(BDART_VALS),
                        "AUART": auart,
                        "KUNNR": kunnr,
                    }
                )
                bucket = "overdue" if requested < ANCHOR else "future"
                d = demand.setdefault((matnr, werks), {"overdue": 0.0, "future": 0.0})
                d[bucket] += open_qty

        if all(s == "C" for s in item_statuses):
            gbstk = "C"
        elif all(s == "A" for s in item_statuses):
            gbstk = "A"
        else:
            gbstk = "B"
        vbak_rows.append(
            {
                "MANDT": MANDT,
                "VBELN": vbeln,
                "ERDAT": _fmt(erdat),
                "ERZET": f"{random.randint(7, 18):02d}{random.randint(0, 59):02d}{random.randint(0, 59):02d}",
                "ERNAM": random.choice(SAP_USERS),
                "AUART": auart,
                "KUNNR": kunnr,
                "NETWR": round(order_netwr, 2),
                "WAERK": waerk,
                "VKORG": "1000",
                "VTWEG": random.choice(["10", "20"]),
                "SPART": random.choice(["01", "02"]),
                "GBSTK": gbstk,
            }
        )

    _write(pd.DataFrame(vbak_rows), "VBAK")
    _write(pd.DataFrame(vbap_rows), "VBAP")
    _write(pd.DataFrame(vbbe_rows), "VBBE")


def gen_resb(ctx: dict) -> pd.DataFrame:
    """Production reservations: withdrawn in the past, open in the future."""
    rows = []
    demand = ctx["demand"]
    rsnum = 0
    resb_combos = random.sample(ctx["marc_combos"], int(len(ctx["marc_combos"]) * 0.5))
    for matnr, werks in resb_combos:
        mp = ctx["mat_persona"][matnr]
        lgort = random.choice(ctx["storage_locs"][werks])
        n_lines = {
            "A": random.randint(10, 18),
            "B": random.randint(6, 12),
            "C": random.randint(2, 6),
        }[mp["class"]]
        for _ in range(n_lines):
            rsnum += 1
            offset = random.randint(-90, 120)
            bddat = _next_wd(ANCHOR + timedelta(days=offset))
            qty = _lognorm(mp["base_qty"] * 0.8, 0.5, 1, 4000)
            if bddat < ANCHOR:
                if random.random() < 0.90:  # consumed
                    enmng, kzear = qty, "X"
                else:  # open overdue -> backlog
                    enmng, kzear = round(qty * random.uniform(0.0, 0.6), 2), ""
                    demand.setdefault((matnr, werks), {"overdue": 0.0, "future": 0.0})[
                        "overdue"
                    ] += round(qty - enmng, 2)
            else:
                enmng, kzear = 0.0, ""
                demand.setdefault((matnr, werks), {"overdue": 0.0, "future": 0.0})["future"] += qty
            rows.append(
                {
                    "MANDT": MANDT,
                    "RSNUM": _pad(rsnum, 10),
                    "RSPOS": _pad(random.randint(1, 10), 4),
                    "RSART": random.choice(["M", "F", "N"]),
                    "MATNR": matnr,
                    "WERKS": werks,
                    "LGORT": lgort,
                    "BDMNG": qty,
                    "ENMNG": enmng,
                    "MEINS": ctx["material_uom"][matnr],
                    "BDDAT": _fmt(bddat),
                    "AUFNR": _pad(random.randint(1, 99999), 12),
                    "VBELN": "",
                    "KZEAR": kzear,
                }
            )
    df = pd.DataFrame(rows)
    _write(df, "RESB")
    return df


# ─── Layer 2b — Planning master data (needs realized demand) ─────────────────


def gen_marc(ctx: dict) -> pd.DataFrame:
    """Planning params sized to realized demand: safety stock ~ demand x lead time."""
    ekgrp_vals = ["B01", "B02", "B03"]
    disls_vals = ["EX", "FX", "MB"]
    dispo_vals = [f"D{i:03d}" for i in range(1, 6)]
    rows = []
    for matnr, werks in ctx["marc_combos"]:
        mp = ctx["mat_persona"][matnr]
        info = ctx["combo_info"][(matnr, werks)]
        d = ctx["demand"].get((matnr, werks), {"overdue": 0.0, "future": 0.0})
        daily_rate = d["future"] / 120.0
        primary_vendor = ctx["mat_vendors"][matnr][0][0]
        plifz = round(ctx["vendor_persona"][primary_vendor]["lt_mean"])
        eisbe = round(max(daily_rate * math.sqrt(plifz) * 1.2, mp["base_qty"] * 0.2), 2)
        minbe = round(eisbe + daily_rate * plifz, 2)
        rows.append(
            {
                "MANDT": MANDT,
                "MATNR": matnr,
                "WERKS": werks,
                "EKGRP": random.choice(ekgrp_vals),
                "DISMM": "PD" if daily_rate > 0 else random.choice(DISMM_VALS),
                "DISPO": random.choice(dispo_vals),
                "DISLS": random.choice(disls_vals),
                "MINBE": minbe,
                "EISBE": eisbe,
                "MABST": round(max(minbe * random.uniform(2, 4), mp["base_qty"] * 2), 2),
                "BESKZ": info["beskz"],
                "PLIFZ": plifz,
                "WEBAZ": random.choices([0, 1, 2, 3], weights=[20, 40, 30, 10])[0],
                "MAABC": mp["class"],
            }
        )
    df = pd.DataFrame(rows)
    _write(df, "MARC")
    return df


def gen_mard(ctx: dict) -> pd.DataFrame:
    """Stock sized to demand coverage; shortage combos get starved on purpose."""
    rows = []
    for matnr, werks in ctx["marc_combos"]:
        mp = ctx["mat_persona"][matnr]
        d = ctx["demand"].get((matnr, werks), {"overdue": 0.0, "future": 0.0})
        daily_rate = d["future"] / 120.0
        if (matnr, werks) in ctx["shortage_combos"]:
            stock = d["overdue"] * random.uniform(0.0, 0.6) + daily_rate * random.uniform(0, 6)
        elif daily_rate == 0 and d["overdue"] == 0:
            stock = mp["base_qty"] * random.uniform(0, 10)  # slow movers / dead stock
        else:
            stock = d["overdue"] * random.uniform(0.9, 1.3) + daily_rate * random.uniform(15, 60)
        lgort_pool = ctx["storage_locs"][werks]
        n_locs = random.randint(1, 2)
        locs = random.sample(lgort_pool, n_locs)
        splits = [random.uniform(0.3, 1.0) for _ in locs]
        total = sum(splits)
        for lgort, frac in zip(locs, splits, strict=False):
            rows.append(
                {
                    "MANDT": MANDT,
                    "MATNR": matnr,
                    "WERKS": werks,
                    "LGORT": lgort,
                    "LABST": round(stock * frac / total, 2),
                    "UMLME": round(daily_rate * random.uniform(0, 3), 2),
                    "INSME": round(daily_rate * random.uniform(0, 2), 2),
                    "SPEME": (
                        round(mp["base_qty"] * random.uniform(0, 1), 2)
                        if random.random() < 0.05
                        else 0.0
                    ),
                    "LFGJA": str(ANCHOR.year),
                    "LFMON": str(ANCHOR.month).zfill(2),
                }
            )
    df = pd.DataFrame(rows)
    _write(df, "MARD")
    return df


# ─── Layer 4 — Transaction MM (purchasing + inbound deliveries) ──────────────


def _plan_po_items(ctx: dict) -> list[dict]:
    """Plan PO line items: historical replenishment + future supply sized to the
    demand-vs-stock gap, split across the material's vendor panel by quota."""
    hist_days = [d for d in _date_range(HIST_START, ANCHOR) if _is_wd(d)]
    hist_weights = [_day_weight(d) for d in hist_days]
    items: list[dict] = []
    for matnr, werks in ctx["marc_combos"]:
        if ctx["combo_info"][(matnr, werks)]["beskz"] != "F":
            continue
        mp = ctx["mat_persona"][matnr]
        d = ctx["demand"].get((matnr, werks), {"overdue": 0.0, "future": 0.0})

        # Historical POs: regular replenishment over 24 months
        n_hist = {"A": random.randint(8, 12), "B": random.randint(4, 8), "C": random.randint(1, 4)}[
            mp["class"]
        ]
        for _ in range(n_hist):
            lifnr = random.choices(
                [v for v, _ in ctx["mat_vendors"][matnr]],
                weights=[s for _, s in ctx["mat_vendors"][matnr]],
            )[0]
            items.append(
                {
                    "matnr": matnr,
                    "werks": werks,
                    "lifnr": lifnr,
                    "bedat": random.choices(hist_days, weights=hist_weights)[0],
                    "qty": _lognorm(mp["base_qty"] * 4, 0.5, 2, 20000),
                    "future": False,
                }
            )

        # Future supply: cover open demand not covered by stock (with noise so a
        # handful of materials end up under-supplied naturally)
        stock_proxy = 0.0 if (matnr, werks) in ctx["shortage_combos"] else d["future"] * 0.3
        need = (d["overdue"] + d["future"] - stock_proxy) * random.uniform(0.7, 1.25)
        if (matnr, werks) in ctx["shortage_combos"]:
            need *= random.uniform(0.1, 0.5)  # starve supply too
        if need <= 0:
            continue
        for lifnr, share in ctx["mat_vendors"][matnr]:
            qty = round(need * share, 2)
            if qty < 1:
                continue
            items.append(
                {
                    "matnr": matnr,
                    "werks": werks,
                    "lifnr": lifnr,
                    "bedat": _next_wd(ANCHOR - timedelta(days=random.randint(1, 30))),
                    "qty": qty,
                    "future": True,
                }
            )
    return items


def gen_purchasing(ctx: dict) -> None:
    """EKKO/EKPO/EKET + inbound LIKP/LIPS + VBUP delivery statuses."""
    planned = _plan_po_items(ctx)
    planned.sort(key=lambda x: (x["lifnr"], x["bedat"]))

    ekko_rows, ekpo_rows, eket_rows = [], [], []
    receipt_events: list[dict] = []  # received goods -> LIKP/LIPS with WBSTK='C'
    asn_events: list[dict] = []  # in transit -> LIKP/LIPS with WBSTK!='C'

    po_seq = 0
    idx = 0
    while idx < len(planned):
        first = planned[idx]
        target_items = random.randint(1, 5)
        group = [first]
        j = idx + 1
        while (
            j < len(planned)
            and len(group) < target_items
            and planned[j]["lifnr"] == first["lifnr"]
            and abs((planned[j]["bedat"] - first["bedat"]).days) <= 7
        ):
            group.append(planned[j])
            j += 1
        idx = j

        po_seq += 1
        ebeln = _pad(4_500_000_000 + po_seq, 10)
        lifnr = first["lifnr"]
        vp = ctx["vendor_persona"][lifnr]
        bedat = first["bedat"]
        waers = random.choices(WAERS_VALS, weights=[80, 15, 5])[0]
        loekz_po = "L" if random.random() < 0.02 else ""
        ekko_rows.append(
            {
                "MANDT": MANDT,
                "EBELN": ebeln,
                "BUKRS": "1000",
                "BSART": random.choices(BSART_VALS, weights=[70, 20, 10])[0],
                "LIFNR": lifnr,
                "EKORG": "1000",
                "EKGRP": random.choice(["B01", "B02", "B03"]),
                "BEDAT": _fmt(bedat),
                "WAERS": waers,
                "STATU": random.choices(["", "1", "4", "5", "7"], weights=[20, 10, 30, 30, 10])[0],
                "LOEKZ": loekz_po,
                "INCO1": random.choice(INCO1_VALS),
                "INCO2": random.choice(["Hamburg", "Rotterdam", "Stuttgart", "Munich", ""]),
            }
        )

        for pos, item in enumerate(group, start=1):
            ebelp = _pad(pos * 10, 5)
            matnr, werks, qty = item["matnr"], item["werks"], item["qty"]
            mp = ctx["mat_persona"][matnr]
            netpr = round(mp["price"] * random.uniform(0.55, 0.75), 2)  # purchase < sales
            loekz_item = "L" if (loekz_po or random.random() < 0.02) else ""

            # Schedule lines: split qty across 1-4 delivery dates
            n_lines = random.choices([1, 2, 3, 4], weights=[40, 30, 20, 10])[0]
            line_qtys = [random.uniform(0.5, 1.5) for _ in range(n_lines)]
            total_w = sum(line_qtys)
            line_qtys = [round(qty * w / total_w, 2) for w in line_qtys]
            fully_received = True
            for etenr, line_qty in enumerate(line_qtys, start=1):
                if item["future"]:
                    eindt = _next_wd(
                        ANCHOR + timedelta(days=random.randint(3, 150) + (etenr - 1) * 7)
                    )
                else:
                    lt = max(3, random.gauss(vp["lt_mean"], vp["lt_std"]))
                    eindt = _next_wd(bedat + timedelta(days=round(lt) + (etenr - 1) * 14))

                # Receipt simulation per vendor persona
                wemng = 0.0
                if not item["future"] and not loekz_item:
                    if random.random() < vp["otd_rate"]:
                        delay = max(-2, round(random.gauss(0, 1.5)))
                    else:
                        delay = round(random.uniform(3, vp["late_extra"] + 8))
                    arrival = _next_wd(eindt + timedelta(days=delay))
                    if arrival <= ANCHOR and eindt <= ANCHOR:
                        wemng = (
                            line_qty
                            if random.random() < 0.93
                            else round(line_qty * random.uniform(0.5, 0.95), 2)
                        )
                        receipt_events.append(
                            {
                                "lifnr": lifnr,
                                "werks": werks,
                                "arrival": arrival,
                                "ebeln": ebeln,
                                "ebelp": ebelp,
                                "matnr": matnr,
                                "qty": wemng,
                                "netpr": netpr,
                                "waers": waers,
                                "eindt": eindt,
                            }
                        )
                    elif arrival <= ANCHOR + timedelta(days=45):
                        # shipped, still on the road -> ASN
                        asn_events.append(
                            {
                                "lifnr": lifnr,
                                "werks": werks,
                                "arrival": arrival,
                                "ebeln": ebeln,
                                "ebelp": ebelp,
                                "matnr": matnr,
                                "qty": line_qty,
                                "netpr": netpr,
                                "waers": waers,
                                "eindt": eindt,
                            }
                        )
                if wemng < line_qty:
                    fully_received = False
                eket_rows.append(
                    {
                        "MANDT": MANDT,
                        "EBELN": ebeln,
                        "EBELP": ebelp,
                        "ETENR": _pad(etenr, 4),
                        "EINDT": _fmt(eindt),
                        "SLFDT": _fmt(eindt + timedelta(days=random.randint(-3, 3))),
                        "MENGE": line_qty,
                        "WEMNG": wemng,
                        "BANFN": _pad(random.randint(1, 9999), 10),
                        "MBDAT": _fmt(eindt - timedelta(days=random.randint(1, 5))),
                        "WADAT": _fmt(eindt - timedelta(days=random.randint(2, 10))),
                    }
                )

            ekpo_rows.append(
                {
                    "MANDT": MANDT,
                    "EBELN": ebeln,
                    "EBELP": ebelp,
                    "MATNR": matnr,
                    "WERKS": werks,
                    "MATKL": ctx["material_group"][matnr],
                    "MENGE": qty,
                    "MEINS": ctx["material_uom"][matnr],
                    "NETPR": netpr,
                    "NETWR": round(qty * netpr, 2),
                    "PSTYP": random.choices(["0", "2", "9"], weights=[70, 20, 10])[0],
                    "ELIKZ": "X" if fully_received and not item["future"] else "",
                    "LOEKZ": loekz_item,
                }
            )

    _write(pd.DataFrame(ekko_rows), "EKKO")
    _write(pd.DataFrame(ekpo_rows), "EKPO")
    _write(pd.DataFrame(eket_rows), "EKET")
    gen_inbound_deliveries(ctx, receipt_events, asn_events)


def gen_inbound_deliveries(ctx: dict, receipts: list[dict], asns: list[dict]) -> None:
    """LIKP/LIPS as inbound deliveries (LFART='EL'), VGBEL -> PO number.
    Received deliveries get VBUP WBSTK='C'; in-transit ASNs stay 'A'/'B'."""
    likp_rows, lips_rows = [], []
    vbup_rows = ctx["vbup_rows"]
    del_seq = 0

    def emit(events: list[dict], received: bool) -> None:
        nonlocal del_seq
        events.sort(key=lambda e: (e["lifnr"], e["arrival"], e["werks"]))
        i = 0
        while i < len(events):
            head = events[i]
            group = [head]
            j = i + 1
            while (
                j < len(events)
                and len(group) < 4
                and events[j]["lifnr"] == head["lifnr"]
                and events[j]["arrival"] == head["arrival"]
                and events[j]["werks"] == head["werks"]
            ):
                group.append(events[j])
                j += 1
            i = j

            del_seq += 1
            vbeln = _pad(8_000_000_000 + del_seq, 10)
            arrival = head["arrival"]
            netwr = round(sum(e["qty"] * e["netpr"] for e in group), 2)
            likp_rows.append(
                {
                    "MANDT": MANDT,
                    "VBELN": vbeln,
                    "LFART": "EL",
                    "ERDAT": _fmt(arrival),
                    "LFDAT": _fmt(head["eindt"]),
                    "WADAT": _fmt(arrival - timedelta(days=random.randint(2, 12))),
                    "WADAT_IST": _fmt(arrival) if received else "",
                    "KUNNR": "",
                    "VKORG": "1000",
                    "VSTEL": head["werks"],
                    "ROUTE": f"R{random.randint(1, 3):05d}",
                    "NETWR": netwr,
                    "WAERK": head["waers"],
                }
            )
            status = "C" if received else random.choice(["A", "B"])
            for pos, e in enumerate(group, start=1):
                posnr = _pad(pos * 10, 6)
                lips_rows.append(
                    {
                        "MANDT": MANDT,
                        "VBELN": vbeln,
                        "POSNR": posnr,
                        "MATNR": e["matnr"],
                        "MATKL": ctx["material_group"][e["matnr"]],
                        "LFIMG": e["qty"],
                        "MEINS": ctx["material_uom"][e["matnr"]],
                        "WERKS": e["werks"],
                        "LGORT": random.choice(ctx["storage_locs"][e["werks"]]),
                        "VGBEL": e["ebeln"],
                        "VGPOS": e["ebelp"],
                        "NETWR": round(e["qty"] * e["netpr"], 2),
                        "BWART": "101",
                        "MBDAT": _fmt(e["eindt"]),
                    }
                )
                vbup_rows.append(
                    {
                        "MANDT": MANDT,
                        "VBELN": vbeln,
                        "POSNR": posnr,
                        "GBSTA": status,
                        "ABSTK": "",
                        "WBSTK": status,
                        "FKSTK": "",
                        "LVSTK": status,
                        "LSSTK": "",
                        "KOSTA": "",
                        "LFGSK": status,
                    }
                )

    emit(receipts, received=True)
    emit(asns, received=False)
    _write(pd.DataFrame(likp_rows), "LIKP")
    _write(pd.DataFrame(lips_rows), "LIPS")


def gen_vbup(ctx: dict) -> pd.DataFrame:
    df = pd.DataFrame(ctx["vbup_rows"])
    _write(df, "VBUP")
    return df


# ─── Main ─────────────────────────────────────────────────────────────────────


def main() -> None:
    global ANCHOR, HIST_START, DEMAND_END, SUPPLY_END, SUFFIX
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--anchor",
        type=lambda s: date.fromisoformat(s),
        default=date.today(),
        help="'Today' for the dataset (YYYY-MM-DD). History/future generated around it.",
    )
    args = parser.parse_args()
    ANCHOR = args.anchor
    HIST_START = ANCHOR - timedelta(days=730)
    DEMAND_END = ANCHOR + timedelta(days=130)
    SUPPLY_END = ANCHOR + timedelta(days=180)
    SUFFIX = f"_{ANCHOR:%Y%m%d}.csv"

    ctx: dict = {}
    print(f"Generating synthetic SAP ECC 6.0 data (anchor = {ANCHOR})...\n")

    print("Layer 0 — Config")
    gen_t001w(ctx)
    gen_tfact(ctx)

    print("\nLayer 1 — Master Data + Personas")
    build_material_personas(ctx)
    gen_mara(ctx)
    gen_kna1(ctx)
    gen_lfa1(ctx)

    print("\nLayer 2 — Material-Plant + Quota")
    build_marc_combos(ctx)
    gen_equk_equp(ctx)

    print("\nLayer 3 — Demand (SD + production)")
    gen_sales(ctx)
    gen_resb(ctx)

    print("\nLayer 2b — Planning Master Data (demand-informed)")
    gen_marc(ctx)
    gen_mard(ctx)

    print("\nLayer 4 — Purchasing + Inbound Deliveries")
    gen_purchasing(ctx)
    gen_vbup(ctx)

    print(f"\nDone. Anchor={ANCHOR}, shortage combos={len(ctx['shortage_combos'])}.")


if __name__ == "__main__":
    main()
