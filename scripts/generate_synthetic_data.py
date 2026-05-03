"""Generate synthetic SAP ECC 6.0 CSV files mimicking SE16 extracts.

Layer 0 → Layer 4 must run in order to preserve FK consistency.
Output: data/raw/se16/<TABLE>/<TABLE>_20241231.csv
"""

import random
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
from faker import Faker

fake = Faker("de_DE")
random.seed(42)
Faker.seed(42)

MANDT = "100"
DATE_START = date(2022, 1, 1)
DATE_END = date(2024, 12, 31)
OUT_DIR = Path("data/raw/se16")
SUFFIX = "_20241231.csv"

AUART_VALS = ["OR", "ZOR", "RE"]
LFART_VALS = ["LF", "LFRE"]
BSART_VALS = ["NB", "FO", "UB"]
MTART_VALS = ["ROH", "FERT", "HALB", "HIBE"]
BESKZ_VALS = ["E", "F", "X"]
DISMM_VALS = ["PD", "VB", "ND"]
STATUS_VALS = ["A", "B", "C"]
BWART_VALS = ["101", "601", "301"]
WAERS_VALS = ["EUR", "USD", "VND"]
MEINS_VALS = ["EA", "KG", "L", "M", "ST"]
INCO1_VALS = ["EXW", "DAP", "CIF", "DDP"]
BDART_VALS = ["KE", "KEL", "LSF"]
SAP_USERS = [f"USER{i:04d}" for i in range(1, 51)]
REGION_CODES = ["BW", "BY", "BE", "SN", "HH", "HE", "NW", "RP"]


def _rdate(start: date = DATE_START, end: date = DATE_END) -> date:
    return start + timedelta(days=random.randint(0, (end - start).days))


def _fmt(d: date) -> str:
    return d.strftime("%Y%m%d")


def _pad(n: int, w: int = 10) -> str:
    return str(n).zfill(w)


def _qty(lo: float = 1.0, hi: float = 500.0) -> float:
    return round(random.uniform(lo, hi), 2)


def _price(lo: float = 10.0, hi: float = 2000.0) -> float:
    return round(random.uniform(lo, hi), 2)


def _write(df: pd.DataFrame, table: str) -> None:
    p = OUT_DIR / table
    p.mkdir(parents=True, exist_ok=True)
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


# ─── Layer 1 — Master Data ───────────────────────────────────────────────────


def gen_mara(ctx: dict, n: int = 500) -> pd.DataFrame:
    mat_groups = ["MG001", "MG002", "MG003", "MG004", "MG005"]
    rows = []
    material_uom: dict[str, str] = {}
    for i in range(1, n + 1):
        matnr = _pad(i, 18)
        meins = random.choice(MEINS_VALS)
        material_uom[matnr] = meins
        rows.append(
            {
                "MANDT": MANDT,
                "MATNR": matnr,
                "MTART": random.choice(MTART_VALS),
                "MBRSH": "M",
                "MATKL": random.choice(mat_groups),
                "MEINS": meins,
                "BRGEW": _qty(0.1, 50.0),
                "GEWEI": "KG",
                "ERSDA": _fmt(_rdate(date(2018, 1, 1), date(2021, 12, 31))),
            }
        )
    df = pd.DataFrame(rows)
    ctx["material_ids"] = [r["MATNR"] for r in rows]
    ctx["material_uom"] = material_uom
    _write(df, "MARA")
    return df


def gen_kna1(ctx: dict, n: int = 100) -> pd.DataFrame:
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
            "ERDAT": _fmt(_rdate(date(2015, 1, 1), date(2021, 12, 31))),
        }
        for i in range(1, n + 1)
    ]
    df = pd.DataFrame(rows)
    ctx["customer_ids"] = [r["KUNNR"] for r in rows]
    _write(df, "KNA1")
    return df


def gen_lfa1(ctx: dict, n: int = 50) -> pd.DataFrame:
    rows = [
        {
            "MANDT": MANDT,
            "LIFNR": _pad(i, 10),
            "LAND1": random.choice(["DE", "AT", "CH", "CN", "JP"]),
            "NAME1": fake.company()[:35],
            "ORT01": fake.city()[:35],
            "PSTLZ": fake.postcode()[:10],
            "REGIO": random.choice(REGION_CODES),
            "KTOKK": "0001",
            "STCD1": "",
            "ERDAT": _fmt(_rdate(date(2015, 1, 1), date(2021, 12, 31))),
            "ERNAM": random.choice(SAP_USERS),
            "SPERR": "",
            "XCPDK": "",
        }
        for i in range(1, n + 1)
    ]
    df = pd.DataFrame(rows)
    ctx["vendor_ids"] = [r["LIFNR"] for r in rows]
    _write(df, "LFA1")
    return df


# ─── Layer 2 — Master Data Extended ─────────────────────────────────────────


def gen_marc(ctx: dict) -> pd.DataFrame:
    ekgrp_vals = ["B01", "B02", "B03"]
    disls_vals = ["EX", "FX", "MB"]
    rows = []
    for matnr in ctx["material_ids"]:
        n_plants = random.randint(1, 3)
        for werks in random.sample(ctx["plant_ids"], min(n_plants, len(ctx["plant_ids"]))):
            lgort_pool = ctx["storage_locs"][werks]
            rows.append(
                {
                    "MANDT": MANDT,
                    "MATNR": matnr,
                    "WERKS": werks,
                    "EKGRP": random.choice(ekgrp_vals),
                    "DISMM": random.choice(DISMM_VALS),
                    "DISLS": random.choice(disls_vals),
                    "MINBE": _qty(10, 200),
                    "EISBE": _qty(5, 100),
                    "MABST": _qty(500, 5000),
                    "BESKZ": random.choice(BESKZ_VALS),
                    "SOBSL": "",
                    "PLIFZ": random.randint(1, 60),
                    "WEBAZ": random.randint(0, 5),
                    "DZEIT": random.randint(0, 30),
                    "LGPRO": random.choice(lgort_pool),
                    "LGFSB": random.choice(lgort_pool),
                    "MMSTA": "",
                }
            )
    df = pd.DataFrame(rows).drop_duplicates(subset=["MATNR", "WERKS"])
    ctx["marc_combos"] = list(zip(df["MATNR"], df["WERKS"], strict=False))
    _write(df, "MARC")
    return df


def gen_mard(ctx: dict) -> pd.DataFrame:
    rows = []
    for matnr, werks in ctx["marc_combos"]:
        lgort_pool = ctx["storage_locs"][werks]
        n_locs = random.randint(1, min(2, len(lgort_pool)))
        for lgort in random.sample(lgort_pool, n_locs):
            rows.append(
                {
                    "MANDT": MANDT,
                    "MATNR": matnr,
                    "WERKS": werks,
                    "LGORT": lgort,
                    "LABST": _qty(0, 1000),
                    "UMLME": _qty(0, 50),
                    "INSME": _qty(0, 30),
                    "EINME": 0.0,
                    "SPEME": 0.0,
                    "RETME": 0.0,
                    "LFGJA": "2024",
                    "LFMON": str(random.randint(1, 12)).zfill(2),
                }
            )
    df = pd.DataFrame(rows)
    ctx["mard_combos"] = list(zip(df["MATNR"], df["WERKS"], df["LGORT"], strict=False))
    _write(df, "MARD")
    return df


def gen_equk(ctx: dict, n: int = 100) -> pd.DataFrame:
    rows = []
    quota_ids: list[str] = []
    for i in range(1, n + 1):
        qunum = _pad(i, 10)
        vdatu = _rdate(date(2022, 1, 1), date(2023, 12, 31))
        bdatu = min(vdatu + timedelta(days=random.randint(180, 730)), DATE_END)
        quota_ids.append(qunum)
        rows.append(
            {
                "MANDT": MANDT,
                "MATNR": random.choice(ctx["material_ids"]),
                "WERKS": random.choice(ctx["plant_ids"]),
                "QUNUM": qunum,
                "VDATU": _fmt(vdatu),
                "BDATU": _fmt(bdatu),
                "SCMNG": _qty(1, 100),
                "ERDAT": _fmt(vdatu),
                "ERNAM": random.choice(SAP_USERS),
            }
        )
    df = pd.DataFrame(rows)
    ctx["quota_ids"] = quota_ids
    _write(df, "EQUK")
    return df


def gen_equp(ctx: dict) -> pd.DataFrame:
    rows = []
    for qunum in ctx["quota_ids"]:
        n_items = random.randint(1, 3)
        remaining = 100.0
        for pos in range(1, n_items + 1):
            pct = round(remaining / (n_items - pos + 1), 1)
            remaining = round(remaining - pct, 1)
            rows.append(
                {
                    "MANDT": MANDT,
                    "QUNUM": qunum,
                    "QUPOS": _pad(pos, 3),
                    "BESKZ": random.choice(BESKZ_VALS),
                    "LIFNR": random.choice(ctx["vendor_ids"]),
                    "BEWRK": random.choice(ctx["plant_ids"]),
                    "QUOTE": pct,
                    "QUBMG": _qty(100, 5000),
                    "QUMNG": _qty(0, 500),
                    "MAXMG": _qty(1000, 10000),
                    "MINLS": _qty(10, 100),
                    "MAXLS": _qty(100, 1000),
                    "PLIFZ": random.randint(1, 60),
                    "PREIH": _pad(pos, 2),
                    "VERID": "",
                }
            )
    df = pd.DataFrame(rows)
    _write(df, "EQUP")
    return df


# ─── Layer 3 — Transaction SD ────────────────────────────────────────────────


def gen_vbak(ctx: dict, n: int = 6000) -> pd.DataFrame:
    rows = []
    order_ids: list[str] = []
    order_customer: dict[str, str] = {}
    order_dates: dict[str, date] = {}
    order_waerk: dict[str, str] = {}
    for i in range(1, n + 1):
        vbeln = _pad(i, 10)
        kunnr = random.choice(ctx["customer_ids"])
        erdat = _rdate()
        waerk = random.choice(WAERS_VALS)
        order_ids.append(vbeln)
        order_customer[vbeln] = kunnr
        order_dates[vbeln] = erdat
        order_waerk[vbeln] = waerk
        rows.append(
            {
                "MANDT": MANDT,
                "VBELN": vbeln,
                "ERDAT": _fmt(erdat),
                "ERZET": f"{random.randint(6, 18):02d}{random.randint(0, 59):02d}{random.randint(0, 59):02d}",
                "ERNAM": random.choice(SAP_USERS),
                "AUART": random.choice(AUART_VALS),
                "KUNNR": kunnr,
                "NETWR": _price(100, 50000),
                "WAERK": waerk,
                "VKORG": "1000",
                "VTWEG": random.choice(["10", "20"]),
                "SPART": random.choice(["01", "02"]),
                "GBSTK": random.choices(STATUS_VALS, weights=[20, 30, 50])[0],
            }
        )
    df = pd.DataFrame(rows)
    ctx["order_ids"] = order_ids
    ctx["order_customer"] = order_customer
    ctx["order_dates"] = order_dates
    ctx["order_waerk"] = order_waerk
    _write(df, "VBAK")
    return df


def gen_vbap(ctx: dict) -> pd.DataFrame:
    pstyv_vals = ["TAN", "TANN", "TATX"]
    rows = []
    order_items: list[tuple[str, str]] = []
    order_item_data: dict[tuple[str, str], dict] = {}
    order_to_items: dict[str, list[tuple[str, str]]] = {}
    for vbeln in ctx["order_ids"]:
        n_items = random.randint(1, 7)
        items_for_order: list[tuple[str, str]] = []
        for pos in range(1, n_items + 1):
            posnr = _pad(pos * 10, 6)
            matnr = random.choice(ctx["material_ids"])
            werks = random.choice(ctx["plant_ids"])
            lgort = random.choice(ctx["storage_locs"][werks])
            meins = ctx["material_uom"][matnr]
            qty = _qty(1, 200)
            order_items.append((vbeln, posnr))
            items_for_order.append((vbeln, posnr))
            order_item_data[(vbeln, posnr)] = {
                "MATNR": matnr,
                "WERKS": werks,
                "LGORT": lgort,
                "MEINS": meins,
                "MENGE": qty,
            }
            rows.append(
                {
                    "MANDT": MANDT,
                    "VBELN": vbeln,
                    "POSNR": posnr,
                    "MATNR": matnr,
                    "MENGE": qty,
                    "MEINS": meins,
                    "NETWR": _price(10, 5000),
                    "WAERK": ctx["order_waerk"][vbeln],
                    "WERKS": werks,
                    "LGORT": lgort,
                    "PSTYV": random.choice(pstyv_vals),
                    "ABGRU": "",
                }
            )
        order_to_items[vbeln] = items_for_order
    df = pd.DataFrame(rows)
    ctx["order_items"] = order_items
    ctx["order_item_data"] = order_item_data
    ctx["order_to_items"] = order_to_items
    _write(df, "VBAP")
    return df


def gen_likp(ctx: dict, coverage: float = 0.90) -> pd.DataFrame:
    chosen_orders = random.sample(ctx["order_ids"], int(len(ctx["order_ids"]) * coverage))
    rows = []
    delivery_ids: list[str] = []
    delivery_order: dict[str, str] = {}
    for i, vbeln_ord in enumerate(chosen_orders, start=1):
        vbeln_del = _pad(8_000_000_000 + i, 10)
        kunnr = ctx["order_customer"][vbeln_ord]
        bldat = ctx["order_dates"][vbeln_ord] + timedelta(days=random.randint(1, 5))
        wadat = bldat + timedelta(days=random.randint(1, 10))
        wadat_ist = wadat + timedelta(days=random.randint(-2, 5))
        delivery_ids.append(vbeln_del)
        delivery_order[vbeln_del] = vbeln_ord
        rows.append(
            {
                "MANDT": MANDT,
                "VBELN": vbeln_del,
                "LFART": random.choice(LFART_VALS),
                "BLDAT": _fmt(min(bldat, DATE_END)),
                "WADAT": _fmt(min(wadat, DATE_END)),
                "WADAT_IST": _fmt(min(wadat_ist, DATE_END)),
                "KODAT": _fmt(min(bldat, DATE_END)),
                "LADDT": _fmt(min(bldat + timedelta(1), DATE_END)),
                "TDDAT": _fmt(min(bldat, DATE_END)),
                "KUNNR": kunnr,
                "KUNAG": kunnr,
                "VKORG": "1000",
                "VSTEL": random.choice(ctx["plant_ids"]),
                "ROUTE": f"R{random.randint(1, 3):05d}",
                "INCO1": random.choice(INCO1_VALS),
                "BTGEW": _qty(1, 500),
                "GEWEI": "KG",
            }
        )
    df = pd.DataFrame(rows)
    ctx["delivery_ids"] = delivery_ids
    ctx["delivery_order"] = delivery_order
    _write(df, "LIKP")
    return df


def gen_lips(ctx: dict) -> pd.DataFrame:
    pstyv_vals = ["TAN", "TANN"]
    rows = []
    for vbeln_del in ctx["delivery_ids"]:
        vbeln_ord = ctx["delivery_order"][vbeln_del]
        items = ctx["order_to_items"].get(vbeln_ord, [])
        if not items:
            continue
        n_del_items = random.randint(1, min(5, len(items)))
        for del_pos, (ord_vbeln, ord_posnr) in enumerate(
            random.sample(items, n_del_items), start=1
        ):
            info = ctx["order_item_data"][(ord_vbeln, ord_posnr)]
            rows.append(
                {
                    "MANDT": MANDT,
                    "VBELN": vbeln_del,
                    "POSNR": _pad(del_pos * 10, 6),
                    "MATNR": info["MATNR"],
                    "LFIMG": info["MENGE"],
                    "LGMNG": info["MENGE"],
                    "VRKME": info["MEINS"],
                    "WERKS": info["WERKS"],
                    "LGORT": info["LGORT"],
                    "CHARG": "",
                    "VGBEL": ord_vbeln,
                    "VGPOS": ord_posnr,
                    "WBSTA": random.choices(["A", "B", "C"], weights=[20, 30, 50])[0],
                    "PSTYV": random.choice(pstyv_vals),
                    "NTGEW": _qty(0.5, 100),
                    "BRGEW": _qty(1, 120),
                }
            )
    df = pd.DataFrame(rows)
    _write(df, "LIPS")
    return df


def gen_vbup(ctx: dict) -> pd.DataFrame:
    rows = [
        {
            "MANDT": MANDT,
            "VBELN": vbeln,
            "POSNR": posnr,
            "GBSTA": random.choices(STATUS_VALS, weights=[20, 30, 50])[0],
            "ABSTK": "",
            "WBSTK": random.choices(["A", "B", "C"], weights=[20, 40, 40])[0],
            "FKSTK": random.choices(["A", "B", "C"], weights=[20, 30, 50])[0],
            "LVSTK": random.choices(["A", "B", "C"], weights=[20, 30, 50])[0],
            "LSSTK": "",
            "KOSTA": "",
            "LFGSK": random.choices(["A", "B", "C"], weights=[20, 30, 50])[0],
        }
        for vbeln, posnr in ctx["order_items"]
    ]
    df = pd.DataFrame(rows)
    _write(df, "VBUP")
    return df


def gen_vbbe(ctx: dict, n: int = 15000) -> pd.DataFrame:
    sample = random.sample(ctx["order_items"], min(n, len(ctx["order_items"])))
    rows = []
    for vbeln, posnr in sample:
        info = ctx["order_item_data"][(vbeln, posnr)]
        req_date = ctx["order_dates"][vbeln] + timedelta(days=random.randint(1, 30))
        rows.append(
            {
                "MANDT": MANDT,
                "MATNR": info["MATNR"],
                "WERKS": info["WERKS"],
                "LGORT": info["LGORT"],
                "BDART": random.choice(BDART_VALS),
                "VBELN": vbeln,
                "POSNR": posnr,
                "BDMNG": info["MENGE"],
                "MEINS": info["MEINS"],
                "BDDAT": _fmt(min(req_date, DATE_END)),
                "AEDAT": _fmt(min(req_date + timedelta(1), DATE_END)),
            }
        )
    df = pd.DataFrame(rows)
    _write(df, "VBBE")
    return df


# ─── Layer 4 — Transaction MM ────────────────────────────────────────────────


def gen_ekko(ctx: dict, n: int = 1800) -> pd.DataFrame:
    ekgrp_vals = ["B01", "B02", "B03"]
    rows = []
    po_ids: list[str] = []
    po_dates: dict[str, date] = {}
    po_currency: dict[str, str] = {}
    for i in range(1, n + 1):
        ebeln = _pad(4_500_000_000 + i, 10)
        bedat = _rdate()
        waers = random.choice(WAERS_VALS)
        po_ids.append(ebeln)
        po_dates[ebeln] = bedat
        po_currency[ebeln] = waers
        rows.append(
            {
                "MANDT": MANDT,
                "EBELN": ebeln,
                "BUKRS": "1000",
                "BSART": random.choice(BSART_VALS),
                "LIFNR": random.choice(ctx["vendor_ids"]),
                "EKORG": "1000",
                "EKGRP": random.choice(ekgrp_vals),
                "BEDAT": _fmt(bedat),
                "WAERS": waers,
            }
        )
    df = pd.DataFrame(rows)
    ctx["po_ids"] = po_ids
    ctx["po_dates"] = po_dates
    ctx["po_currency"] = po_currency
    _write(df, "EKKO")
    return df


def gen_ekpo(ctx: dict) -> pd.DataFrame:
    rows = []
    po_items: list[tuple[str, str]] = []
    po_item_data: dict[tuple[str, str], dict] = {}
    for ebeln in ctx["po_ids"]:
        n_items = random.randint(1, 5)
        for pos in range(1, n_items + 1):
            ebelp = _pad(pos * 10, 5)
            matnr = random.choice(ctx["material_ids"])
            werks = random.choice(ctx["plant_ids"])
            meins = ctx["material_uom"][matnr]
            qty = _qty(1, 500)
            eindt = ctx["po_dates"][ebeln] + timedelta(days=random.randint(7, 90))
            po_items.append((ebeln, ebelp))
            po_item_data[(ebeln, ebelp)] = {
                "MATNR": matnr,
                "WERKS": werks,
                "MEINS": meins,
                "MENGE": qty,
                "EINDT": eindt,
            }
            rows.append(
                {
                    "MANDT": MANDT,
                    "EBELN": ebeln,
                    "EBELP": ebelp,
                    "MATNR": matnr,
                    "MENGE": qty,
                    "MEINS": meins,
                    "NETPR": _price(5, 1000),
                    "PEINH": 1.0,
                    "WERKS": werks,
                    "EINDT": _fmt(min(eindt, DATE_END)),
                    "ELIKZ": random.choices(["", "X"], weights=[60, 40])[0],
                }
            )
    df = pd.DataFrame(rows)
    ctx["po_items"] = po_items
    ctx["po_item_data"] = po_item_data
    _write(df, "EKPO")
    return df


def gen_eket(ctx: dict) -> pd.DataFrame:
    rows = []
    for ebeln, ebelp in ctx["po_items"]:
        item = ctx["po_item_data"][(ebeln, ebelp)]
        eindt = item["EINDT"]
        gr_qty = round(item["MENGE"] * random.uniform(0, 1), 2)
        gr_date = min(eindt + timedelta(days=random.randint(0, 10)), DATE_END)
        rows.append(
            {
                "MANDT": MANDT,
                "EBELN": ebeln,
                "EBELP": ebelp,
                "ETENR": "0001",
                "EINDT": _fmt(min(eindt, DATE_END)),
                "SLFDT": _fmt(min(eindt + timedelta(days=random.randint(-3, 3)), DATE_END)),
                "MENGE": item["MENGE"],
                "WEMNG": gr_qty,
                "WEDAT": _fmt(gr_date) if gr_qty > 0 else "",
                "GLMNG": round(item["MENGE"] - gr_qty, 2),
                "BANFN": _pad(random.randint(1, 9999), 10),
                "BNFPO": _pad(random.randint(1, 5) * 10, 5),
            }
        )
    df = pd.DataFrame(rows)
    _write(df, "EKET")
    return df


def gen_mkpf(ctx: dict, n: int = 3000) -> pd.DataFrame:
    rows = []
    matdoc_ids: list[tuple[str, str]] = []
    matdoc_dates: dict[tuple[str, str], date] = {}
    for i in range(1, n + 1):
        mblnr = _pad(5_000_000_000 + i, 10)
        budat = _rdate()
        mjahr = str(budat.year)
        matdoc_ids.append((mblnr, mjahr))
        matdoc_dates[(mblnr, mjahr)] = budat
        rows.append(
            {
                "MANDT": MANDT,
                "MBLNR": mblnr,
                "MJAHR": mjahr,
                "BLDAT": _fmt(budat),
                "BUDAT": _fmt(budat),
                "USNAM": random.choice(SAP_USERS),
                "CPUDT": _fmt(budat),
            }
        )
    df = pd.DataFrame(rows)
    ctx["matdoc_ids"] = matdoc_ids
    ctx["matdoc_dates"] = matdoc_dates
    _write(df, "MKPF")
    return df


def gen_mseg(ctx: dict) -> pd.DataFrame:
    rows = []
    for mblnr, mjahr in ctx["matdoc_ids"]:
        n_items = random.randint(1, 4)
        for zeile in range(1, n_items + 1):
            matnr = random.choice(ctx["material_ids"])
            werks = random.choice(ctx["plant_ids"])
            rows.append(
                {
                    "MANDT": MANDT,
                    "MBLNR": mblnr,
                    "MJAHR": mjahr,
                    "ZEILE": _pad(zeile, 4),
                    "BWART": random.choice(BWART_VALS),
                    "MATNR": matnr,
                    "WERKS": werks,
                    "LGORT": random.choice(ctx["storage_locs"][werks]),
                    "MENGE": _qty(1, 500),
                    "MEINS": ctx["material_uom"][matnr],
                    "DMBTR": _price(10, 50000),
                    "WAERS": random.choice(WAERS_VALS),
                    "BUDAT": _fmt(ctx["matdoc_dates"][(mblnr, mjahr)]),
                }
            )
    df = pd.DataFrame(rows)
    _write(df, "MSEG")
    return df


def gen_resb(ctx: dict, n: int = 1500) -> pd.DataFrame:
    rows = []
    for i in range(1, n + 1):
        matnr = random.choice(ctx["material_ids"])
        werks = random.choice(ctx["plant_ids"])
        lgort = random.choice(ctx["storage_locs"][werks])
        req_qty = _qty(1, 300)
        withdrawn = round(req_qty * random.uniform(0, 1), 2)
        req_date = _rdate()
        rows.append(
            {
                "MANDT": MANDT,
                "RSNUM": _pad(i, 10),
                "RSPOS": _pad(random.randint(1, 10), 4),
                "RSART": random.choice(["M", "F", "N"]),
                "MATNR": matnr,
                "WERKS": werks,
                "LGORT": lgort,
                "BDMNG": req_qty,
                "ENMNG": withdrawn,
                "MEINS": ctx["material_uom"][matnr],
                "BDDAT": _fmt(min(req_date, DATE_END)),
                "AUFNR": "",
                "VBELN": random.choice(ctx["order_ids"]) if random.random() < 0.5 else "",
                "KZEAR": "X" if withdrawn >= req_qty else "",
            }
        )
    df = pd.DataFrame(rows)
    _write(df, "RESB")
    return df


# ─── Main ─────────────────────────────────────────────────────────────────────


def main() -> None:
    ctx: dict = {}
    print("Generating synthetic SAP ECC 6.0 data...\n")

    print("Layer 0 — Config")
    gen_t001w(ctx)
    gen_tfact(ctx)

    print("\nLayer 1 — Master Data")
    gen_mara(ctx)
    gen_kna1(ctx)
    gen_lfa1(ctx)

    print("\nLayer 2 — Master Data Extended")
    gen_marc(ctx)
    gen_mard(ctx)
    gen_equk(ctx)
    gen_equp(ctx)

    print("\nLayer 3 — Transaction SD")
    gen_vbak(ctx)
    gen_vbap(ctx)
    gen_likp(ctx)
    gen_lips(ctx)
    gen_vbup(ctx)
    gen_vbbe(ctx)

    print("\nLayer 4 — Transaction MM")
    gen_ekko(ctx)
    gen_ekpo(ctx)
    gen_eket(ctx)
    gen_mkpf(ctx)
    gen_mseg(ctx)
    gen_resb(ctx)

    print("\nDone.")


if __name__ == "__main__":
    main()
