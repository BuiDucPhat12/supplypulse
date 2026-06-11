# SupplyPulse — Data Lineage & Logic Reference

> Tài liệu này ghi lại lineage, business logic, và những điểm cần lưu ý cho toàn bộ dbt pipeline.
> Cập nhật: 2026-05-28

---

## Kiến trúc tổng quan

```
Bronze (PostgreSQL, schema: bronze)
    ↓ 1:1 rename/cast
Staging (schema: staging, materialized: view)
    ↓ business logic
Intermediate (schema: intermediate, materialized: table)
    ↓ aggregation + simulation
Marts (schema: analytics, materialized: table)
```

**Anchor date:** `DATE '2024-09-01'` dùng thay `CURRENT_DATE` vì synthetic data chỉ cover đến 2024-12-31. Khi regenerate data với future dates → đổi lại `CURRENT_DATE`.

**Cửa sổ simulation:** 120 ngày từ anchor date = `2024-09-01` → `2024-12-29`.

---

## Surrogate Key Convention

| Key | Formula | Ý nghĩa |
|-----|---------|---------|
| `marc_id` | `material_number \|\| '-' \|\| plant` | Material × Plant |
| `ekpo_id` | `po_number \|\| '-' \|\| po_item` | PO line |
| `lfa1_id` | `vendor_number` | Vendor (dùng trực tiếp, không composite) |

> ⚠️ **Khác production:** Production dùng `logsys-matnr-werks` (3 parts). SupplyPulse bỏ `logsys` vì synthetic data chỉ có 1 logical system.

---

## Date Arithmetic Pattern (Cách 2)

Dùng để tính `planned_availability_date = start_date + N working days`.

```sql
-- Cách 1 (cũ, bị lỗi với cuối tuần): double-join int_working_calendar
LEFT JOIN wc wc1 ON plant = wc1.plant AND start_date = wc1.calendar_date  -- FAIL nếu cuối tuần
LEFT JOIN wc wc2 ON plant = wc2.plant AND wc2.working_day_index = wc1.idx + N

-- Cách 2 (đúng, hiện tại): fc xử lý cuối tuần, wc tính offset
LEFT JOIN fc ON plant = fc.plant AND start_date = fc.calendar_date
LEFT JOIN wc ON plant = wc.plant
           AND wc.working_day_index = fc.technical_day_number
                                    + (CASE WHEN fc.is_workingday = 0 THEN 1 ELSE 0 END)
                                    + N
```

`fc` (int_factory_calendar) cover mọi ngày kể cả cuối tuần → không bị miss.
`(CASE WHEN is_workingday = 0 THEN 1 ELSE 0 END)` = snap cuối tuần sang working day kế tiếp trước khi cộng N.

Dùng ở: `int_sa_future`, `int_inbound_deliveries_asn`.

---

## Staging Layer

> Tất cả view, schema: staging. Logic chủ yếu là rename + cast, không có business logic phức tạp.

### stg_marc
**Raw:** `bronze.MARC` — Material Planning Data per Plant
| Column | Raw field | Notes |
|--------|-----------|-------|
| `marc_id` | `matnr \|\| '-' \|\| werks` | Surrogate key |
| `gr_processing_days` | `WEBAZ` | Số ngày xử lý GR sau khi hàng đến (dùng nhiều ở Phase E) |
| `safety_stock` | `EISBE` | |
| `procurement_type` | `BESKZ` | F=external, E=internal |
| `mrpc` | `DISPO` | MRP controller code |

### stg_mard
**Raw:** `bronze.MARD` — Stock by Storage Location
| Column | Raw field | Notes |
|--------|-----------|-------|
| `unrestricted_stock` | `LABST` | Available stock |
| `blocked_stock` | `KLABS` | Blocked (DISKZ='1') |
| `quality_inspection_stock` | `INSME` | Quality hold |

> ⚠️ `KLABS` và `DISKZ` bị bỏ khỏi bronze trong schema rework (2026-05-10). `available_stock` trong int_pn_infor = `LABST` only.

### stg_ekko
**Raw:** `bronze.EKKO` — PO/SA Header
| Column | Raw field | Notes |
|--------|-----------|-------|
| `vendor_number` | `LIFNR` | Dùng để trace vendor từ LIPS (reference_document → ekko.po_number) |
| `deletion_flag` | `LOEKZ` | Filter `NOT IN ('L','S','X')` ở int_purchasing_document_active |

### stg_ekpo
**Raw:** `bronze.EKPO` — PO/SA Line Items
| Column | Raw field | Notes |
|--------|-----------|-------|
| `ekpo_id` | `ebeln \|\| '-' \|\| ebelp` | Surrogate key |
| `marc_id` | `matnr \|\| '-' \|\| werks` | Join key với MARC |
| `deletion_flag` | `LOEKZ` | Filter cùng với EKKO |

> ⚠️ **FK gap đã fix (2026-05-28):** gen_ekpo() trước đây chọn matnr+werks độc lập → tạo combos không có trong MARC → NULL available_stock. Fix: chọn từ `marc_combos`.

### stg_eket
**Raw:** `bronze.EKET` — SA Delivery Schedule Lines
| Column | Raw field | Notes |
|--------|-----------|-------|
| `ekpo_id` | `ebeln \|\| '-' \|\| ebelp` | Join key với EKPO |
| `delivery_date` | `EINDT` | Ngày giao hàng theo lịch SA |
| `open_quantity` | `MENGE - WEMNG` | Tính tại staging (production dùng OMENGE) |

> ⚠️ Production có cột `OMENGE` riêng. SupplyPulse tính `open_quantity = scheduled_quantity - goods_receipt_quantity` vì bronze thiếu OMENGE.

### stg_vbup
**Raw:** `bronze.VBUP` — SD Document Item Status
| Column | Raw field | Notes |
|--------|-----------|-------|
| `document_number` | `VBELN` | **Generic SD doc number** — có thể là SO, delivery, billing |
| `document_item` | `POSNR` | |
| `goods_movement_status` | `WBSTK` | Filter `!= 'C'` ở int_inbound_deliveries_asn |

> ⚠️ **Đã fix (2026-05-27):** Tên cũ `sales_order_id` sai vì VBELN trong VBUP là generic SD doc, không phải chỉ SO. Đổi sang `document_number`.

### stg_likp
**Raw:** `bronze.LIKP` — Delivery Header
| Column | Raw field | Notes |
|--------|-----------|-------|
| `customer_number` | `KUNNR` | ⚠️ Là customer nhận hàng, **không phải vendor**. Vendor lấy từ EKKO qua LIPS.reference_document |
| `actual_goods_issue_date` | `WADAT_IST` | NULL nếu chưa xử lý GR |
| `gr_date` | computed | `COALESCE(LEAST(created_date, actual_goods_issue_date), created_date)` = budat_mkpf equiv |

### stg_lips
**Raw:** `bronze.LIPS` — Delivery Line Items
| Column | Raw field | Notes |
|--------|-----------|-------|
| `reference_document` | `VGBEL` | PO number (EBELN) — dùng để trace vendor |
| `reference_item` | `VGPOS` | PO item |
| `delivery_quantity` | `LFIMG` | ASN quantity |

### stg_lfa1
**Raw:** `bronze.LFA1` — Vendor Master
| Column | Raw field | Notes |
|--------|-----------|-------|
| `vendor_number` | `LIFNR` | Primary key |
| `country` | `LAND1` | Dùng trong int_transit_time |

### stg_t001w
**Raw:** `bronze.T001W` — Plant Master
| Column | Raw field | Notes |
|--------|-----------|-------|
| `factory_calendar_key` | `FABKL` | Join key sang TFACT, dùng trong int_factory_calendar |

---

## Intermediate Layer

### int_factory_calendar
**Sources:** `stg_t001w` + `generate_series`
**Grain:** 1 plant × 1 calendar date

| Column | Logic | Notes |
|--------|-------|-------|
| `is_workingday` | `DOW NOT IN (0,6)` | Simplified: bỏ qua ngày lễ |
| `jump_to_wd_date` | Sat+2, Sun+1, else self | Snap cuối tuần → Monday |
| `technical_day_number` | `SUM(is_workingday) OVER (ORDER BY date)` | Cumulative working days. Bằng `working_day_index` của wc với working days |

> ⚠️ Range: `2024-01-01` → `2025-06-30`. Mở rộng từ ban đầu (`2024-09-01` + 180 ngày) để cover historical LIKP dates.

### int_working_calendar
**Sources:** `int_factory_calendar WHERE is_workingday = 1`
**Grain:** 1 plant × 1 working date

`working_day_index = ROW_NUMBER() OVER (PARTITION BY plant ORDER BY calendar_date)`

Consistent với `technical_day_number` trong factory_calendar: với mọi working day, `working_day_index = technical_day_number`.

### int_material_bbm
**Sources:** `stg_marc`
**Grain:** 1 material × 1 plant (`marc_id`)

Bảng nền tảng FK — `int_backlog` INNER JOIN với model này để filter chỉ lấy demand của valid materials.

### int_pn_infor
**Sources:** `int_material_bbm` LEFT JOIN `stg_mard`

**Grain:** 1 marc_id

| Column | Logic | Notes |
|--------|-------|-------|
| `available_stock` | `COALESCE(SUM(LABST), 0)` | 0 nếu có MARC nhưng không có MARD row |
| `blocked_stock_s` | `COALESCE(SUM(KLABS), 0)` | |
| `blocked_stock_q` | `COALESCE(SUM(INSME), 0)` | |

> ⚠️ NULL vs 0: nếu marc_id không có trong int_pn_infor → LEFT JOIN downstream ra **NULL** (không phải 0). Xảy ra khi material có PO nhưng không có MARC — đã fix bằng gen_ekpo() dùng marc_combos.

### int_backlog
**Sources:** `stg_resb` UNION ALL `stg_vbbe` → INNER JOIN `int_material_bbm`

**Grain:** 1 demand line (hoặc null row per material)

| Column | Logic |
|--------|-------|
| `backlog_per_pn` | `SUM(demand_qty) WHERE requirement_date < '2024-09-01'` per marc_id |
| `backlog_per_pn_contype` | Same nhưng per marc_id + demand_source + requirement_type |

**Null row pattern:** Nếu material có overdue demand nhưng **không có** future rows (requirement_date >= anchor) → tạo 1 row với tất cả NULL trừ `backlog_per_pn`. Mục đích: giữ overdue signal cho inventory simulation dù không có future demand rows.

**Filter future:** `requirement_date BETWEEN '2024-09-01' AND '2024-09-01' + 120 days`

### int_purchasing_document_active
**Sources:** `stg_ekko` INNER JOIN `stg_ekpo`
**Grain:** 1 PO line (`ekpo_id`)

Filter: `COALESCE(deletion_flag, '') NOT IN ('L', 'S', 'X')` — áp dụng cả EKKO và EKPO level.

### int_purchasing_document_tt
**Sources:** `int_purchasing_document_active` + `int_transit_time` + `int_valid_quote_agreements`
**Grain:** 1 PO line

LEFT JOIN cả TT và quota (PO có thể không có TT hoặc không có quota arrangement).

Guard fan-out: `MAX(quote_percent) GROUP BY material+plant+vendor` trước khi join.

### int_equk_active / int_equp_active
**Sources:** `stg_equk` / `stg_equp`

Dedup bằng `ROW_NUMBER() OVER (PARTITION BY material+plant+end_date ORDER BY created_date DESC)`.

`int_equk_active`: filter `CURRENT_DATE BETWEEN valid_from AND valid_to` → dùng `DATE '2024-09-01'` thay thế.

### int_valid_quote_agreements
**Sources:** `int_equk_active` INNER JOIN `int_equp_active` LEFT JOIN `stg_lfa1`
**Grain:** 1 quota arrangement × 1 vendor item

`quote_percent = quota / NULLIF(SUM(quota) OVER (PARTITION BY quota_arrangement_number), 0)`

### int_transit_time
**Sources:** `seed_transit_time` LEFT JOIN `stg_lfa1` + `stg_t001w`

Seed thay thế SAP custom table `rb04` (không có trong standard ECC).

### int_tt_quota
**Sources:** `int_purchasing_document_tt`
**Grain:** 1 marc_id × 1 vendor_number

```sql
GROUP BY marc_id, vendor_number → MAX(transit_time_days), MAX(quote_percent)
max_tt = MAX(transit_time_days) OVER (PARTITION BY marc_id)
```

`max_tt` = TT của vendor chậm nhất cho material này. Dùng trong `mart_shortage_report` để tính `end_of_tt_gr`.

### int_sa_by_delivery_date
**Sources:** `stg_eket`
**Grain:** 1 ekpo_id × 1 delivery_date

GROUP BY ekpo_id + delivery_date: SUM scheduled/received/open quantity.
Lý do: EKET có nhiều schedule lines (ETENR) cùng ngày → gộp thành 1 dòng per ngày.

### int_scheduling_agreement
**Sources:** `int_purchasing_document_active` INNER JOIN `int_sa_by_delivery_date`
**Grain:** 1 ekpo_id × 1 delivery_date

INNER JOIN: chỉ giữ PO lines có ít nhất 1 delivery schedule. PO active nhưng chưa có EKET → bỏ qua.

### int_sa_future
**Sources:** `int_scheduling_agreement` + `int_purchasing_document_tt` + `stg_marc` + `int_factory_calendar` + `int_working_calendar` + `stg_lfa1` + `int_valid_quote_agreements`
**Grain:** 1 ekpo_id × 1 delivery_date (với open_quantity > 0)

**Tính `planned_availability_date`:** Cách 2 pattern (xem phần trên).
- `delivery_date` → `fc.technical_day_number` → `wc.working_day_index + gr_processing_days` → `planned_availability_date`
- COALESCE fallback: `delivery_date + gr_processing_days` (calendar days) khi ngoài range

> ⚠️ Không filter theo ngày — SA lines với delivery_date trong quá khứ nhưng `open_quantity > 0` vẫn được giữ. Chúng được phân loại là overdue supply.

### int_inbound_deliveries
**Sources:** `stg_likp` INNER JOIN `stg_lips` LEFT JOIN `stg_vbup` LEFT JOIN `stg_marc`

**`gr_date`** = `COALESCE(LEAST(created_date, actual_goods_issue_date), created_date)`
- Production gọi là `budat_mkpf = MIN(erdat, wadat_ist)`
- `actual_goods_issue_date` NULL cho pending deliveries → fallback về `created_date`

> ⚠️ Vendor không có trong LIKP. Lấy vendor qua: `lips.reference_document` = PO number → join `stg_ekko.po_number` → `stg_ekko.vendor_number`.

### int_inbound_deliveries_asn
**Sources:** `int_inbound_deliveries` + `stg_ekko` + `int_factory_calendar` + `int_working_calendar` + `int_valid_quote_agreements`

**Filter:** `goods_movement_status != 'C'` (chưa GR hoàn tất)

**`planned_availability_date`:** Cách 2 pattern từ `gr_date` + `gr_processing_days`

**`asn_status`:**
- `'future'` — PAD >= anchor date → ASN sắp đến, là supply
- `'overdue'` — PAD < anchor date → ASN đáng ra đến rồi nhưng chưa confirm
- `'pending'` — PAD IS NULL → gr_date ngoài calendar range

**`asn_total_due_qty`:** Window SUM của delivery_quantity cho overdue/pending rows, PARTITION BY marc_id (tổng toàn material, không phân biệt vendor).

### int_sa_late_shipment
**Sources:** `int_sa_future` + `int_inbound_deliveries_asn WHERE asn_status = 'future'`

**`cumulative_asn_qty`:** Correlated subquery — tổng ASN từ cùng vendor cho cùng material mà `asn.planned_availability_date <= sa.planned_availability_date`.

**`order_qty_due`** = `open_quantity - cumulative_asn_qty` (phần chưa được cover bởi ASN)

**`late_shipment_flag = 1`** khi **cả 2**:
1. `delivery_date + transit_time_days >= '2024-09-01'` — còn trong TT window (hàng đang trên đường)
2. `order_qty_due > 0` — ASN chưa cover đủ

> Nếu chỉ có điều kiện 2: sẽ flag cả những SA đã qua TT window → đó là shortage thực sự, không phải late shipment.

### int_supply
**Sources:** `int_sa_late_shipment` UNION ALL `int_inbound_deliveries_asn WHERE asn_status = 'future'`

| supply_type | Source | order_qty | order_qty_due | fulfill_qty |
|-------------|--------|-----------|---------------|-------------|
| `'Order Qty'` | int_sa_late_shipment | open_quantity | order_qty_due | cumulative_asn_qty |
| `'ASN'` | int_inbound_deliveries_asn | delivery_quantity | asn_total_due_qty | NULL |

ASN `'overdue'` không được UNION — đã quá hạn, không phải future supply. Được xử lý riêng qua `asn_total_due_qty` ở mart_inventory_simulation.

### int_partial_detail_supply
**Sources:** `int_supply` + `int_pn_infor` + `int_tt_quota` + `int_factory_calendar`
**Grain:** 1 supply event (marc_id × vendor × planned_availability_date)

**Filter:** `planned_availability_date IS NOT NULL`

Kết hợp supply events với context của material (stock, planning params) và calendar info.

### int_fill_missing_dates_supply
**Sources:** `int_partial_detail_supply` + `int_factory_calendar`

**Mục đích:** `mart_inventory_simulation` dùng running SUM OVER (ORDER BY date). Nếu thiếu ngày, SQL bỏ qua và sum nhảy cóc → inventory sai. Model này bù tất cả ngày thiếu trong 120-day window với qty=0.

**Logic:**
1. Lấy tất cả (marc_id, vendor_number, plant) với `supply_type = 'Order Qty'`
2. JOIN factory_calendar (120-day window) → full grid
3. NOT EXISTS → chỉ lấy ngày chưa có trong partial_detail_supply
4. Fill với 0

---

## Marts Layer

### mart_detail_supply
**Sources:** `int_partial_detail_supply` UNION ALL `int_fill_missing_dates_supply`

Fill rows có NULL cho tất cả cột từ pn_infor và tt_quota (available_stock, safety_stock, max_tt...). **Không ảnh hưởng mart_inventory_simulation** vì simulation source trực tiếp từ int_pn_infor.

### mart_consumption
**Sources:** `int_backlog WHERE requirement_date IS NOT NULL`

GROUP BY marc_id + requirement_date → `SUM(demand_qty) AS daily_consumption`

Null rows từ int_backlog (requirement_date IS NULL) được exclude.

### mart_inventory_simulation
**Sources:** `int_pn_infor` + `int_factory_calendar` + `int_backlog` + `int_inbound_deliveries_asn`

**Base grid:** `int_pn_infor` JOIN `int_factory_calendar` (120-day window) → material × day matrix

**Công thức:**
```
simulated_inventory_qty =
    available_stock          -- hằng số (tồn kho hiện tại)
  - backlog_qty              -- hằng số per material (overdue demand đã tích lũy trước anchor)
  - SUM(daily_consumption) OVER (PARTITION BY marc_id ORDER BY calendar_date)
  + SUM(daily_asn_qty)     OVER (PARTITION BY marc_id ORDER BY calendar_date)
```

> **Tại sao `backlog_qty` không cần SUM OVER?**
> `backlog_per_pn` là lượng demand đã quá hạn TRƯỚC khi simulation bắt đầu — nó là debt tích lũy từ trước, không phát sinh thêm theo ngày. Trừ trực tiếp ngay từ ngày đầu.
> `daily_consumption` là demand phát sinh TỪNG NGÀY trong tương lai → cần tích lũy.

`simulated_inventory_qty < 0` = red day (thiếu hàng ngày đó).

### mart_shortage_report
**Sources:** `mart_inventory_simulation` + `int_tt_quota`
**Grain:** 1 marc_id (summary per material)

| Column | Logic |
|--------|-------|
| `end_of_tt_gr` | `anchor_date + max_tt` — ngày muộn nhất vendor chậm nhất có thể giao |
| `red_days` | `COUNT(*) FILTER (WHERE simulated_inventory_qty < 0)` — toàn 120 ngày |
| `min_qty_in_tt_gr` | `MIN(simulated_inventory_qty) WHERE calendar_date <= end_of_tt_gr` |
| `status` | `'Shortage'` nếu có red day trong `[anchor, end_of_tt_gr]` |

> **Tại sao `status` chỉ check trong TT window?**
> Trong `[anchor, end_of_tt_gr]`: hàng đang trên đường — không can thiệp kịp. Inventory âm = shortage không tránh được.
> Sau `end_of_tt_gr`: còn thời gian đặt hàng mới để bù. Inventory âm ở đây là planning issue, không phải immediate shortage.

---

## Known Issues & Limitations

| Issue | Ảnh hưởng | Workaround |
|-------|-----------|------------|
| `is_workingday` chỉ dựa trên thứ (Mon–Fri), bỏ qua ngày lễ | `planned_availability_date` hơi sai vào dịp lễ | Acceptable cho portfolio demo |
| Synthetic LIKP là outbound delivery (SD), không phải inbound (MM) | `customer_number` thay vì `vendor_number` trên header | Trace vendor qua `reference_document → ekko` |
| `DATE '2024-09-01'` hardcoded | Mọi "future" logic bị anchor cố định | Đổi sang `CURRENT_DATE` khi regenerate data |
| SA lines với past `delivery_date` vẫn vào pipeline | Past dates trong mart_detail_supply | Không ảnh hưởng mart_inventory_simulation |

---

## Build Order

```
Phase A — Staging (15 models, tất cả views)

Phase B — Foundations
  seed_transit_time → int_material_bbm → int_pn_infor → int_backlog
  int_purchasing_document_active
  int_equk_active → int_equp_active → int_valid_quote_agreements
  int_transit_time

Phase C — Calendar
  int_factory_calendar → int_working_calendar

Phase D — PO + SA + ASN
  int_purchasing_document_tt
  int_sa_by_delivery_date → int_scheduling_agreement
  int_inbound_deliveries

Phase E — Future Supply & ASN
  int_sa_future
  int_inbound_deliveries_asn
  int_sa_late_shipment

Phase F — Supply Consolidation
  int_tt_quota → int_supply
  int_partial_detail_supply → int_fill_missing_dates_supply

Phase G — Marts
  mart_detail_supply
  mart_consumption
  mart_inventory_simulation → mart_shortage_report
```
