# Step 1.2 — Generate Synthetic SAP Data

> **Status:** PLAN — chưa bắt đầu code
> **Mục tiêu:** Tạo CSV files giả lập đúng schema SAP ECC 6.0, đủ referential integrity để chạy pipeline end-to-end mà không dùng data thật của Bosch.

---

## 1. Quyết định scope

| # | Quyết định | Giá trị | Lý do |
|---|---|---|---|
| D1 | Date range | 2022-01-01 → 2024-12-31 | 3 năm đủ để test seasonal pattern, không quá nặng |
| D2 | Volume mode | Dev volume (~10% ước tính thật) | Đủ chạy pipeline, nhanh generate, dễ debug |
| D3 | MANDT (SAP client) | `100` | Chuẩn SAP sandbox/dev |
| D4 | Plant codes | `1000`, `1001`, `1002`, '1003' | Bosch-style 4-digit numeric |
| D5 | Output path | `data/raw/se16/<TABLE>/<TABLE>_20241231.csv` | Giả lập 1 lần extract cuối năm |
| D6 | Encoding | UTF-8, comma delimiter | Standard cho downstream pipeline |
| D7 | NULL representation | empty string ` ` | Không dùng `NULL` hay `\N` |

---

## 2. Volume mục tiêu (dev)

| Layer | Bảng | Rows | Ghi chú |
|---|---|---|---|
| 0 — Config | T001W | 4 | 4 plants: 1000, 1001, 1002, 1003 |
| 0 — Config | TFACT | 3 | 1 factory calendar per plant |
| 1 — Master | MARA | 500 | Mix ROH/FERT/HALB |
| 1 — Master | KNA1 | 100 | Customers |
| 1 — Master | LFA1 | 50 | Vendors |
| 2 — Master ext | MARC | ~1,000 | ~2 plant per material avg |
| 2 — Master ext | MARD | ~1,500 | ~1.5 storage loc per MARC row |
| 2 — Master ext | EQUK | 100 | Quota arrangement headers |
| 2 — Master ext | EQUP | 200 | ~2 items per quota avg |
| 3 — TX SD | VBAK | 6,000 | Sales order headers |
| 3 — TX SD | VBAP | 24,000 | ~4 items per order |
| 3 — TX SD | LIKP | 5,400 | ~85% orders get a delivery |
| 3 — TX SD | LIPS | 18,000 | ~3.3 items per delivery |
| 3 — TX SD | VBUP | 24,000 | 1:1 với VBAP |
| 3 — TX SD | VBBE | 15,000 | Open requirements |
| 4 — TX MM | EKKO | 1,800 | PO headers |
| 4 — TX MM | EKPO | 5,400 | ~3 items per PO |
| 4 — TX MM | EKET | 5,400 | 1:1 với EKPO (1 schedule line each) |
| 4 — TX MM | MKPF | 3,000 | Material document headers |
| 4 — TX MM | MSEG | 7,500 | ~2.5 items per material doc |
| 4 — TX MM | RESB | 1,500 | Reservations |
| **Total** | | **~120,000** | Master data ~3.5K + Transaction ~117K |

---

## 3. Thứ tự generate (FK dependency)

Bắt buộc generate theo thứ tự — bảng sau dùng ID của bảng trước.

```
Layer 0 — Config (không có FK)
    T001W  →  sinh ra: plant_ids = ['1000', '1001', '1002', '1003']
    TFACT  →  sinh ra: calendar_ids

Layer 1 — Master Data
    MARA   →  sinh ra: material_ids (500 MATNR)
    KNA1   →  sinh ra: customer_ids (100 KUNNR)
    LFA1   →  sinh ra: vendor_ids   (50 LIFNR)

Layer 2 — Master Data mở rộng
    MARC   →  FK: MATNR × WERKS
    MARD   →  FK: MATNR × WERKS × LGORT
    EQUK   →  FK: MATNR, WERKS
    EQUP   →  FK: QUNUM (từ EQUK), LIFNR

Layer 3 — Transaction SD
    VBAK   →  FK: KUNNR, VKORG
    VBAP   →  FK: VBELN (từ VBAK), MATNR, WERKS
    LIKP   →  FK: KUNNR; trace về VBAK
    LIPS   →  FK: VBELN (LIKP), MATNR, VGBEL (VBAK), VGPOS (VBAP)
    VBUP   →  FK: VBELN (VBAK), POSNR (VBAP) — 1:1
    VBBE   →  FK: MATNR, WERKS, VBELN (VBAK), POSNR (VBAP)

Layer 4 — Transaction MM
    EKKO   →  FK: LIFNR (LFA1)
    EKPO   →  FK: EBELN (EKKO), MATNR, WERKS
    EKET   →  FK: EBELN (EKKO), EBELP (EKPO)
    MKPF   →  standalone header (MBLNR, MJAHR)
    MSEG   →  FK: MBLNR (MKPF), MATNR, WERKS, LGORT
    RESB   →  FK: MATNR, WERKS, LGORT; optional FK VBELN (VBAK)
```

---

## 4. SAP formatting rules

Các field SAP có format đặc thù — phải đúng để pipeline sau không bị lỗi parse.

| Field type | SAP format | Ví dụ |
|---|---|---|
| CHAR(10) doc number | Left-pad zeros, 10 ký tự | `0000012345` |
| NUMC(6) item number | Left-pad zeros, 6 ký tự | `000010`, `000020` (tăng 10) |
| DATS | `YYYYMMDD` string, không có dash | `20240315` |
| TIMS | `HHMMSS` string | `143022` |
| CURR / QUAN | Decimal, 2 chữ số thập phân | `1500.00` |
| MANDT | Fixed `100` | `100` |
| MATNR | Left-pad zeros, 18 ký tự | `000000000000000123` |
| KUNNR / LIFNR | Left-pad zeros, 10 ký tự | `0000000042` |

---

## 5. Realistic value sets

Để data trông thật, dùng các giá trị SAP chuẩn thay vì random string.

| Field | Allowed values |
|---|---|
| AUART (order type) | `OR`, `ZOR`, `RE` |
| LFART (delivery type) | `LF`, `LFRE` |
| BSART (PO type) | `NB`, `FO`, `UB` |
| MTART (material type) | `ROH`, `FERT`, `HALB`, `HIBE` |
| BESKZ (procurement type) | `E`, `F`, `X` |
| DISMM (MRP type) | `PD`, `VB`, `ND` |
| GBSTK / status flags | `A` (open), `B` (partial), `C` (complete) |
| BWART (movement type in MSEG) | `101` (GR PO), `601` (GI delivery), `301` (transfer) |
| WAERK / WAERS | `EUR`, `USD`, `VND` |
| MEINS | `EA`, `KG`, `L`, `M`, `ST` |
| INCO1 | `EXW`, `DAP`, `CIF`, `DDP` |

---

## 6. Cấu trúc code

```
scripts/
  generate_synthetic_data.py    ← 1 file, chia hàm gen_<TABLE>()
  generate_sap_design_excel.py  ← đã có

data/
  raw/
    se16/
      T001W/
        T001W_20241231.csv
      MARA/
        MARA_20241231.csv
      ...   (1 folder per table)
```

**Design pattern:**

```python
# Shared context — giữ IDs đã sinh để FK consistent
ctx = {
    "plant_ids": [],
    "material_ids": [],
    "customer_ids": [],
    "vendor_ids": [],
    "order_ids": [],      # VBAK
    "order_items": [],    # (VBELN, POSNR) pairs
    "po_ids": [],         # EKKO
    ...
}

def gen_t001w(ctx) -> pd.DataFrame: ...
def gen_mara(ctx)  -> pd.DataFrame: ...
# ...
def main():
    ctx = {}
    gen_t001w(ctx)   # populates ctx["plant_ids"]
    gen_mara(ctx)    # populates ctx["material_ids"]
    # ...
```

---

## 7. Validation sau khi generate

Trước khi sang Step 1.3, tự check:

| # | Check | Cách kiểm tra |
|---|---|---|
| V1 | Mọi VBAP.VBELN tồn tại trong VBAK | `pd.merge(vbap, vbak, on='VBELN', how='left')` — không có NaN |
| V2 | Mọi LIPS.VGBEL tồn tại trong VBAK | Tương tự |
| V3 | Mọi EKPO.EBELN tồn tại trong EKKO | Tương tự |
| V4 | Không có MATNR nào trong VBAP mà không có trong MARA | Tương tự |
| V5 | Row count đúng với target | `len(df)` cho từng bảng |
| V6 | Không có NULL trong PK fields | `df[pk_cols].isnull().sum() == 0` |
| V7 | DATS fields đúng format YYYYMMDD | `pd.to_datetime(df['ERDAT'], format='%Y%m%d')` — không lỗi |

---

## 8. Dependencies cần thêm

```bash
uv add faker pandas
```

---

## 9. Self-check trước khi sang Step 1.3

1. Bạn giải thích được tại sao phải generate Layer 0 trước Layer 3?
2. MATNR trong SAP ECC có format gì? Tại sao phải left-pad?
3. Nếu LIPS.VGBEL không match VBAK.VBELN, pipeline Bronze → Silver sẽ bị lỗi ở đâu?
