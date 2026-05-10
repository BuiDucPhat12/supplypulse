 # Notes: Logic & Lưu ý — Step 1.2 Synthetic Data

> **Liên quan:** `scripts/generate_synthetic_data.py` + `tests/test_generate_synthetic_data.py`
> **Ngày:** 2026-05-03

---

## 1. Generator — `generate_synthetic_data.py`

### 1.1 Shared context (`ctx`)

Toàn bộ script dùng 1 dict `ctx` truyền qua tất cả hàm `gen_*()`.
Mỗi hàm **đọc** FK từ ctx và **ghi** IDs mới vào ctx để các hàm sau dùng.

```
gen_t001w  → ctx["plant_ids"], ctx["storage_locs"], ctx["calendar_ids"]
gen_mara   → ctx["material_ids"], ctx["material_uom"]
gen_kna1   → ctx["customer_ids"]
gen_lfa1   → ctx["vendor_ids"]
gen_marc   → ctx["marc_combos"]
gen_mard   → ctx["mard_combos"]
gen_equk   → ctx["quota_ids"]
gen_vbak   → ctx["order_ids"], ctx["order_customer"], ctx["order_dates"], ctx["order_waerk"]
gen_vbap   → ctx["order_items"], ctx["order_item_data"], ctx["order_to_items"]
gen_likp   → ctx["delivery_ids"], ctx["delivery_order"]
gen_ekko   → ctx["po_ids"], ctx["po_dates"], ctx["po_currency"]
gen_ekpo   → ctx["po_items"], ctx["po_item_data"]
gen_mkpf   → ctx["matdoc_ids"], ctx["matdoc_dates"]
```

**Lưu ý:** Nếu đổi thứ tự gọi hàm trong `main()`, script sẽ bị `KeyError` vì FK chưa được seed.

---

### 1.2 Thứ tự Layer — tại sao bắt buộc

| Layer | Bảng | Phụ thuộc |
|---|---|---|
| 0 — Config | T001W, TFACT | Không có FK |
| 1 — Master | MARA, KNA1, LFA1 | Cần plant_ids từ Layer 0 |
| 2 — Master ext | MARC, MARD, EQUK, EQUP | Cần material_ids, vendor_ids, plant_ids |
| 3 — TX SD | VBAK→VBAP→LIKP→LIPS→VBUP→VBBE | Cần customer_ids, material_ids |
| 4 — TX MM | EKKO→EKPO→EKET, MKPF→MSEG, RESB | Cần vendor_ids, material_ids |

Trong Layer 3, thứ tự nội bộ cũng quan trọng:
- `gen_vbak` phải trước `gen_vbap` (VBAP cần order_ids)
- `gen_vbap` phải trước `gen_likp`, `gen_lips`, `gen_vbup`, `gen_vbbe`
- `gen_likp` phải trước `gen_lips` (LIPS cần delivery_ids)

---

### 1.3 SAP formatting rules

| Field type | Format | Helper |
|---|---|---|
| Doc number (VBELN, EBELN, MBLNR) | 10 ký tự, left-pad zeros | `_pad(n, 10)` |
| Item number (POSNR, EBELP) | 5–6 ký tự, tăng theo 10 | `_pad(pos * 10, 6)` |
| Material (MATNR) | 18 ký tự, left-pad zeros | `_pad(i, 18)` |
| Customer/Vendor (KUNNR, LIFNR) | 10 ký tự, left-pad zeros | `_pad(i, 10)` |
| Date (ERDAT, BEDAT...) | `YYYYMMDD` string, không có dash | `_fmt(d)` |
| MANDT | Fixed `"100"` | constant |

---

### 1.4 `order_to_items` — tại sao cần dict riêng

Trong `gen_lips`, cần lấy danh sách VBAP items của 1 order cụ thể.

Nếu dùng list filter:
```python
items = [(v, p) for (v, p) in ctx["order_items"] if v == vbeln_ord]
# → O(n) cho mỗi delivery = O(5400 × 24000) = ~130M phép so sánh
```

Với `order_to_items` dict (build sẵn trong `gen_vbap`):
```python
items = ctx["order_to_items"].get(vbeln_ord, [])
# → O(1) lookup
```

---

### 1.5 Các giá trị SAP realistic

Không dùng random string — dùng đúng code SAP chuẩn để pipeline sau không bị lỗi mapping:

| Field | Values |
|---|---|
| AUART (order type) | `OR`, `ZOR`, `RE` |
| LFART (delivery type) | `LF`, `LFRE` |
| BSART (PO type) | `NB`, `FO`, `UB` |
| MTART (material type) | `ROH`, `FERT`, `HALB`, `HIBE` |
| BWART (movement type) | `101` (GR-PO), `601` (GI-delivery), `301` (transfer) |
| GBSTK / status | `A` (open), `B` (partial), `C` (complete) |
| MEINS | `EA`, `KG`, `L`, `M`, `ST` |

---

### 1.6 Volume thực tế vs plan

| Bảng | Plan | Actual | Ghi chú |
|---|---|---|---|
| VBAP | 24,000 | 24,005 | randint(1,7) avg=4 × 6000 orders |
| LIPS | 18,000 | 12,311 | Thấp hơn — nhiều orders chỉ có 1-2 items. Không ảnh hưởng FK. |
| EKPO | 5,400 | 5,358 | randint(1,5) avg=3 × 1800 POs |
| MSEG | 7,500 | 7,465 | randint(1,4) avg=2.5 × 3000 MKPF |
| **Total** | ~120K | **114,615** | |

---

## 2. Test — `test_generate_synthetic_data.py`

### 2.1 Cấu trúc

- **Session-scoped fixture `tables`**: load tất cả CSV 1 lần duy nhất cho cả test session — tránh đọc file 54 lần.
- **`pytest.skip`** nếu CSV chưa tồn tại: test không fail khi chưa chạy generator.
- **`dtype=str`** khi đọc CSV: giữ đúng SAP format (leading zeros không bị mất).

---

### 2.2 Bug đã fix — false positive FK checks

**Version cũ (sai):**
```python
merged = pd.merge(vbap, vbak[["VBELN"]], on="VBELN", how="left")
assert merged["VBELN"].notna().all()  # luôn True vì VBELN lấy từ left table
```

Trong pandas left join, cột join key trong result luôn đến từ left table → không bao giờ null dù FK bị broken.

**Version đúng:**
```python
missing = ~vbap["VBELN"].isin(set(vbak["VBELN"]))
assert not missing.any(), f"{missing.sum()} rows with VBELN not in VBAK"
```

**Quy tắc:** Khi cần check FK integrity trong pandas, dùng `isin()` hoặc `indicator=True` trong merge — không check cột join key sau left join.

---

### 2.3 Composite FK — dùng `zip` + `set`

Khi FK là composite key (nhiều cột), `isin()` không dùng được trực tiếp. Dùng:

```python
mkpf_keys = set(zip(mkpf["MBLNR"], mkpf["MJAHR"], strict=False))
mseg_keys = zip(mseg["MBLNR"], mseg["MJAHR"], strict=False)
missing = sum(1 for k in mseg_keys if k not in mkpf_keys)
assert missing == 0
```

---

### 2.4 Phân loại tests (54 tests)

| Nhóm | Số tests | Mục đích |
|---|---|---|
| FK integrity (V1–V5 + 4 extended) | 9 | Referential integrity qua tất cả FK chính |
| PK not null (V6) | 16 | Không có null trong primary key |
| DATS format (V7) | 6 | Date fields đúng format `YYYYMMDD` |
| No duplicate PK | 10 | Không có duplicate rows trên PK |
| SAP field format | 5 | MATNR=18 chars, VBELN=10 chars, MANDT="100" |
| Volume minimum | 8 | Row count đạt ngưỡng tối thiểu |

---

### 2.5 FK checks còn thiếu (chưa test)

Các FK này chưa có test — để lại cho Phase sau khi load vào Postgres:

- MARC.MATNR → MARA
- MARD.MATNR → MARA, MARD.WERKS → T001W
- VBAP.WERKS → T001W
- EKPO.WERKS → T001W
- EKKO.LIFNR → LFA1
- RESB.VBELN → VBAK (optional FK — 50% rows có giá trị, 50% empty)

RESB.VBELN cần xử lý đặc biệt: chỉ check những rows có VBELN != "".

---

## 3. Lưu ý khi tái generate

Nếu cần chạy lại script (ví dụ tăng volume, thêm bảng):

1. `uv run python scripts/generate_synthetic_data.py` — overwrite toàn bộ CSV
2. `uv run pytest tests/test_generate_synthetic_data.py -v` — verify lại
3. CSV không được commit (đã có trong `.gitignore`) — chỉ commit script và test

Seed cố định (`random.seed(42)`, `Faker.seed(42)`) đảm bảo kết quả reproducible mỗi lần chạy.
