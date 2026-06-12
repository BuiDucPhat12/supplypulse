# Synthetic Data v2 — Tiêu chí & Implementation

> Vấn đề với v1: dashboard nhìn "không follow theo cái gì" — vì data có FK integrity
> nhưng **không có statistical structure** (mọi thứ uniform random) và **không có
> causal structure** (status/qty không liên quan đến ngày tháng).
> v2 viết lại `scripts/generate_synthetic_data.py` theo 6 tiêu chí dưới đây.

## Tiêu chí → Implementation

### 1. Anchor-relative dates (bỏ workaround `DATE '2024-09-01'`)

| | v1 | v2 |
|---|---|---|
| "Hôm nay" | Không có — data dừng cứng 2024-12-31 | `--anchor` (default `date.today()`) |
| Lịch sử | uniform 2022→2024 | `ANCHOR - 730d` → `ANCHOR` |
| Tương lai | Không có | demand đến `+130d`, supply đến `+180d` |

Hệ quả cho dbt: các model dùng `DATE '2024-09-01'` (`int_backlog`, `int_equk_active`,
`int_factory_calendar` range cứng 2024-01-01→2025-06-30) **phải đổi sang `CURRENT_DATE`**
và calendar range phải động theo `CURRENT_DATE` ± interval.

File suffix output = `_<ANCHOR:YYYYMMDD>.csv` (mô phỏng ngày extract SE16),
test suite tự đọc anchor từ tên file.

### 2. Phân phối lệch thay vì uniform

- **ABC material classes**: 50 A / 100 B / 350 C. Class quyết định popularity weight
  (A: 6–12, C: 0.3–1.5) và base order qty (lognormal mean 60/25/8).
  → Verify: top 20% materials = ~86% tổng qty (test `test_v8_demand_is_pareto_skewed`).
- **Zipf share**: customer weight `1/rank^0.9`, vendor share `1/rank^0.85`
  → vài key accounts/vendors chiếm phần lớn volume.
- **Lognormal quantities** (`random.lognormvariate`) thay cho `uniform(1, 500)`.

### 3. Time-series structure

`_day_weight(d) = trend × seasonality × weekday`:
- trend: +25% qua 24 tháng
- seasonality: ±18% sine theo ngày trong năm (peak ~tháng 5)
- weekday: Mon–Fri có trọng số, weekend = 0 (orders chỉ rơi working days)

Order dates được sample theo weight này → chart demand theo tháng có hình dạng thật,
và là nền cho Phase 6 forecasting (Prophet/LightGBM có gì đó để học).

### 4. Entity personas

- **Vendor** (`vendor_persona`): `lt_mean` (7–40d), `lt_std`, `otd_rate` (0.86–0.98),
  và **3 bad vendors** (`otd_rate` 0.45–0.62, late_extra 5–20d).
  Mọi schedule line receipt simulate từ persona → vendor scorecard phân hóa thật
  (đo được OTD 0.41 → 0.90 từ data).
- **Material**: giá bán ổn định per material; giá mua = giá bán × 0.55–0.75.
- **Vendor panel per material**: 1–3 vendors, share chuẩn hóa — dùng nhất quán cho
  cả EQUP (quota) lẫn EKKO (PO thật) → `int_valid_quote_agreements` join có nghĩa.

### 5. Causal consistency

- Status suy ra từ ngày so với anchor:
  - SO item: requested quá 90 ngày → `C`; trong 90 ngày → 92% `C`, 8% kẹt `B` (backlog);
    tương lai → `A`. VBAK.GBSTK gộp từ items.
  - VBBE chỉ chứa item **thật sự còn open** (OMENG = phần chưa giao).
- `WEMNG > 0` chỉ khi `EINDT <= anchor` VÀ hàng đã về (`arrival <= anchor`).
- `EKPO.NETWR = MENGE × NETPR`; `VBAK.NETWR = Σ items`; `LIKP.NETWR = Σ LIPS`.
- `ELIKZ = 'X'` chỉ khi mọi schedule line nhận đủ.

### 6. LIKP/LIPS = INBOUND deliveries + cân bằng cung–cầu có chủ đích

- **Đổi semantics**: v1 sinh LIKP/LIPS là outbound (VGBEL → VBAK) trong khi dbt
  intermediate layer (theo production DALI) coi chúng là inbound ASN và trace vendor
  qua `lips.reference_document → ekko`. v2: `LFART='EL'`, `VGBEL → EKKO.EBELN`,
  received → VBUP `WBSTK='C'`, in-transit ASN → `'A'/'B'` + `WADAT_IST` rỗng.
- **Stock sized to demand**: `MARD.LABST ≈ overdue×(0.9–1.3) + daily_rate×(15–60 ngày)`.
- **Future supply sized to gap**: PO tương lai cover `(overdue + future demand − stock proxy)
  × noise(0.7–1.25)`, chia cho vendor panel theo quota share.
- **Anomaly injection**: 8% combos (`shortage_combos`) bị cắt cả stock lẫn supply
  → `mart_shortage_report` ra mix Shortage/No Shortage thay vì random đỏ/xanh.
- MARC planning params demand-informed: `EISBE ≈ daily_rate×√PLIFZ×1.2`,
  `MAABC` = ABC class thật (không random).

## Thay đổi schema/test cần biết

- **Bỏ MKPF + MSEG + cả gen function** (bronze đã bỏ từ Step 1.3). KNA1 vẫn giữ.
- Test V2 đổi: `LIPS.VGBEL ∈ EKKO` (trước là ∈ VBAK).
- Test V5 mới: `EKPO.(MATNR,WERKS) ∈ MARC` — chính là fix `marc_combos` (2026-05-28),
  giờ được enforce bằng test.
- Thêm nhóm test V8 (causal & statistical realism) — 74 tests total.
- VBUP giờ chứa cả delivery items (8_0xx range) lẫn SO items — đúng bản chất
  "generic SD doc" đã ghi nhận hôm 2026-05-27.

## Checklist sau khi regenerate

1. `python scripts/generate_synthetic_data.py` (anchor = hôm nay)
2. Rebuild bronze: `create_tables.sql` → `load_bronze.py`
3. Sửa dbt: `DATE '2024-09-01'` → `CURRENT_DATE` (int_backlog, int_equk_active,
   int_sa_late_shipment, mart_*) và `int_factory_calendar` range → động
4. `dbt build`
5. Mở lại Streamlit cockpit — giờ mới có chuyện để kể
