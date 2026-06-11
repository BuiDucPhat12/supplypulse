# Production DALI — Logic Summary

## Tổng quan

Pipeline biến đổi dữ liệu SAP thô (Oracle) thành bảng mô phỏng tồn kho tương lai 4 tháng.
Mục tiêu: xác định ngày nào tồn kho âm (thiếu hàng) cho từng vật liệu.

Tất cả bảng đều thuộc schema `dali_prod_data`. Dữ liệu thô nằm ở `dali_raw_data`.

---

## Sơ đồ phụ thuộc (thứ tự thực thi)

```
[RAW: marc, mard, eket, ekko, ekpo, vbbe, resb, likp, vbup, rb04, lfa1, t001w, equk, equp, fac_calender, bom_parent_child]
        │
        ▼
Layer 1: Material Master
  material_bbm → material_active → inventory_of_raw_material_active → raw_material
  PN_Infor  ( marc + mard → stock + planning params )
        │
        ▼
Layer 2: Calendar
  working_calendar                        (index ngày làm việc theo thứ tự)
  factory_calendar_inventory_simulation   (thêm jump_to_wd, prev/next_wd)
        │
        ▼
Layer 3: Quota & Transit Time
  equk_bbm_last → equk_bbm_active
  equp_bbm_last → equp_bbm_active
  valid_quote_agreements   ( tỷ lệ quota % mỗi nhà cung cấp )
  rb04_yl1_ediwkn_bbm_active  ( transit time master )
        │
        ▼
Layer 4: Purchasing Documents
  purchasing_document_active         ( EKKO + EKPO đang active )
  purchasing_document_transit_time   ( + TT + quota % )
        │
        ▼
Layer 5: Demand (Backlog)
  backlog   ( RESB + VBBE: nhu cầu tương lai + backlog quá hạn )
        │
        ▼
Layer 6: Supply Schedule
  scheduling_agreement_by_delivery_date   ( EKET gom theo ngày giao )
  scheduling_agreement                    ( + PO header )
  total_due_scheduling_agreement          ( SA quá hạn → tính planned availability date )
  total_due_scheduling_agreement_groupped ( tổng qty quá hạn )
  scheduling_agreement_future             ( SA tương lai + planned availability date )
  scheduling_agreement_late_shipment      ( late shipment flag theo 120 ngày )
        │
        ▼
Layer 7: Inbound Deliveries (ASN)
  inbound_deliveries                ( LIKP + VBUP_LIPS )
  inbound_deliveries_asn            ( + planned availability date + ASN due qty )
        │
        ▼
Layer 8: Supply Consolidation
  supply                 ( Order Qty + ASN gộp chung )
  TT_Quota               ( TT + quota % per material/vendor/MMSA )
  partial_detail_supply  ( PN_Infor × TT_Quota × Supply )
  fill_missing_dates_supply  ( bù ngày còn thiếu trong 120 ngày )
  final_detail_supply        ( partial + filled )
        │
        ▼
Layer 9: Inventory Simulation
  inventory_simulation   ( mô phỏng tồn kho theo ngày )
        │
        ▼
Layer 10: End Tables (tính bởi Go)
  Consumption            ( nhu cầu theo ngày )
  inventory_simulation   ( kết quả cuối: red_days, status, shortage )
  detail_supply          ( chuỗi cung ứng chi tiết )
  pn_next_level          ( BOM traversal )
```

---

## Chi tiết từng layer

### Layer 1 — Material Master

#### `material_bbm`
- **Nguồn:** `dali_raw_data.marc`
- **Output:** `marc_bbm_id` = `logsys-matnr-werks`, `webaz` (GR processing days), `matnr`
- **Mục đích:** Bảng khóa ngoại nền tảng cho toàn pipeline

#### `PN_Infor` ⭐
- **Nguồn:** `marc` LEFT JOIN `mard`
- **Output chính:**

| Cột | Ý nghĩa |
|-----|---------|
| `Available_Stock` | `LABST + KLABS` (khi `DISKZ != '1'`) |
| `Blocked_Stock_S` | `LABST + SPEME` (khi `DISKZ = '1'`) hoặc chỉ `SPEME` |
| `Blocked_Stock_Q` | `INSME` (tồn kho kiểm soát chất lượng) |
| `Safety_time` | `SHZET` |
| `Safety_time_indicator` | `SHFLG` cast sang int |
| `Safety_Stock` | `EISBE` |
| `Processing_Time` | `WEBAZ` (ngày xử lý GR) |
| `FC` | `FXHOR` (Planning Time Fence) |
| `Proc_Type` | `BESKZ` (F=external, E=internal) |
| `MRPC` | `DISPO` (MRP controller) |

- **Kỹ thuật:** Window SUM theo `(logsys, matnr, werks, DISKZ, lgort)` để gộp nhiều kho
- **Phân vùng:** Hash 10 partitions theo `material_id`

---

### Layer 2 — Calendar

#### `working_calendar`
- **Nguồn:** `fac_calender` WHERE `is_workingday = '1'`
- **Logic:** `ROW_NUMBER() OVER (PARTITION BY ident, logsys ORDER BY calendar_dt)` → `working_day_index`
- **Dùng để:** Tính "ngày làm việc thứ N" — cộng N ngày làm việc từ một ngày bất kỳ

#### `factory_calendar_inventory_simulation`
- **Nguồn:** Toàn bộ `fac_calender` (cả ngày không làm việc)
- **Output bổ sung:**

| Cột | Ý nghĩa |
|-----|---------|
| `technical_day_number` | Tổng ngày làm việc tích lũy đến hôm nay |
| `jump_to_wd_date` | Ngày làm việc kế tiếp (dùng cho ngày không làm việc) |
| `prev_wd` | Ngày làm việc trước đó |
| `prev_day_is_not_wd` | Flag ngày trước là ngày nghỉ |
| `next_day_is_not_wd` | Flag ngày sau là ngày nghỉ |

- **Filter:** `calendar_dt >= CURRENT_DATE` (chỉ tương lai)
- **Index:** `(logsys, ident, calendar_dt)`

> **Pattern dùng chung cho date arithmetic:**
> ```sql
> -- Cộng webaz ngày làm việc từ ngày X:
> JOIN working_calendar wc ON calendar_dt = X
> JOIN working_calendar wc2 ON wc2.technical_day_number = wc.technical_day_number + webaz
>                          AND wc2.is_workingday = 1
> -- Kết quả: wc2.jump_to_wd_date = ngày đến hàng
> ```

---

### Layer 3 — Quota & Transit Time

#### `equk_bbm_last` / `equk_bbm_active`
- **Nguồn:** `dali_raw_data.equk` (SAP: Quota Arrangement Header)
- **Logic:** Dedup bằng `ROW_NUMBER() OVER (PARTITION BY logsys-matnr-werks-bdatu ORDER BY erdat DESC)`
- **Active check:** `CURRENT_DATE BETWEEN vdatu_n AND bdatu_n`

#### `valid_quote_agreements`
- **Nguồn:** `equk_bbm_active` JOIN `equp_bbm_active`
- **Logic quota:**
  ```sql
  total_quote = SUM(quote) OVER (PARTITION BY logsys, qunum)
  quote_percent = quote / NULLIF(total_quote, 0)
  ```
- **Ý nghĩa:** Khi vật liệu có nhiều nhà cung cấp, `quote_percent` xác định tỷ lệ đặt hàng với mỗi nhà

#### `TT_Quota`
- **Nguồn:** `marc → purchasing_document_active → rb04 → lfa1 → valid_quote_agreements`
- **Output:** Transit time + quota % per `(material, vendor, MMSA)`
- **`Max_TT`:** TT lớn nhất trong số các nhà cung cấp có quota hợp lệ

---

### Layer 4 — Purchasing Documents

#### `purchasing_document_active`
- **Nguồn:** `ekko` INNER JOIN `ekpo` JOIN `marc`
- **Filter:** `ekpo.loekz NOT IN ('L', 'S', 'X')` (loại bỏ dòng đã xóa)
- **Surrogate keys:**
  - `ekpo_bbm_id` = `logsys-ebeln-ebelp`
  - `marc_bbm_id` = `logsys-matnr-werks`
  - `transport_time_join_id` = `logsys-werks-lifnr-evers`
  - `rb04_yl1_ediwkn_bbm_id` = `logsys-ekorg-werks-lifnr-evers`

#### `purchasing_document_transit_time`
- Bổ sung `rb04_yl1_transt` (transit time) và `quote_percent` vào PO

---

### Layer 5 — Demand (Backlog)

#### `backlog`
- **Nguồn:** UNION ALL của `dali_raw_data.resb` (production orders) + `dali_raw_data.vbbe` (sales orders)
- **Key fields:** `bdart` (demand type), `bdter` (need date), `bdmng` (qty), `baugr` (assembly/parent PN)
- **Logic overdue:**
  ```sql
  backlog_per_pn_contype = SUM(bdmng) WHERE bdter < TODAY   -- theo loại + matnr+werks
  backlog_per_pn         = SUM(bdmng) WHERE bdter < TODAY   -- chỉ theo matnr+werks
  ```
- **Null row rule:** Nếu vật liệu có backlog quá hạn nhưng không có dòng tương lai → tạo row với `bdter=NULL`, `bdmng=NULL` để giữ thông tin backlog
- **Filter:** `bdter` trong khoảng hôm nay đến +4 tháng
- **Phân vùng:** Hash 10 partitions theo `marc_bbm_id`

---

### Layer 6 — Supply Schedule (Scheduling Agreements)

#### `scheduling_agreement_by_delivery_date`
- Gom `eket` theo `(ekpo_bbm_id, eindt)`: SUM `menge`, `wemng`, `omenge`

#### `scheduling_agreement`
- JOIN `purchasing_document_active` + `scheduling_agreement_by_delivery_date`
- Mỗi dòng = 1 PO line × 1 ngày giao hàng

#### `scheduling_agreement_future` ⭐
- **Filter:** `omenge != 0` và `logsys IN (danh sách hệ thống)`
- **Tính `planned_availability_date`:**
  ```
  eindt (ngày GR theo lịch) → tra working_calendar → +webaz ngày làm việc → planned_availability_date
  ```
- **Fallback:** Nếu `planned_availability_date` không trong khoảng hợp lệ → null row tổng hợp

#### `scheduling_agreement_late_shipment` ⭐⭐
- **Mục đích:** Xác định dự án vận chuyển trễ (trong cửa sổ transit time)
- **Logic:**
  1. Tạo date series 120 ngày (hôm nay đến +120)
  2. Cross join với từng SA
  3. Join `inbound_deliveries_asn` để lấy ASN thực tế
  4. Tính `fulfill_qty` tích lũy:
     ```sql
     fulfill_qty = SUM(order_qty - asn) OVER (ORDER BY date) + initial_due_gap
     ```
  5. `late_shipment_flag = 1` khi `date <= end_tt` (còn trong TT window) VÀ `fulfill_qty > 0` (còn thiếu hàng)

---

### Layer 7 — Inbound Deliveries (ASN)

#### `inbound_deliveries`
- **Nguồn:** `likp` (delivery header) JOIN `vbup_lips` (items) JOIN `marc`
- **`budat_mkpf`:** `MIN(erdat, wadat_ist)` — ngày GR thực tế sớm nhất

#### `inbound_deliveries_asn` ⭐⭐
Chuỗi tính toán phức tạp:

```
inbound_deliveries
    → + webaz ngày làm việc (từ gr_date)
    → planned_availability_date
    → asn_total_due_qty (tổng ASN quá hạn)
    → 3 loại output:
        1. planned_availability_date >= TODAY          → ASN tương lai (có qty)
        2. planned_availability_date < TODAY, không còn row tương lai → overdue marker
        3. planned_availability_date IS NULL, due_qty <= 0 → completed marker
```

**Filter ASN active:** `vbup.wbsta != 'C'` (chưa GR hoàn toàn)

**Key:** Sử dụng `availability_date_id = mmsa-vendor` để group quota

---

### Layer 8 — Supply Consolidation

#### `supply`
```sql
SELECT ... 'Order Qty', order_qty_due, planned_availability_date, order_qty, fulfill_qty
FROM scheduling_agreement_late_shipment
UNION ALL
SELECT ... 'ASN', asn_total_due_qty, planned_availability_date, asn_quantity, NULL
FROM inbound_deliveries_asn
```

#### `partial_detail_supply`
- Join: `PN_Infor` × `TT_Quota` × `Supply` × `factory_calendar`
- Mỗi dòng = 1 vật liệu × 1 nhà cung cấp × 1 MMSA × 1 ngày
- Chỉ giữ ngày có trong factory calendar
- Phân vùng hash 10 partitions

#### `fill_missing_dates_supply`
- Tìm các nhóm `(marc_bbm_id, vendor, mmsa, type='Order Qty')` có < 120 ngày
- Bù thêm ngày còn thiếu với `qty=0, fulfill_qty=0`

#### `final_detail_supply`
```sql
SELECT * FROM partial_detail_supply
UNION ALL
SELECT * FROM fill_missing_dates_supply
```

---

### Layer 9 — Inventory Simulation (SQL)

**Staging schema `staging_inv` tạo 14 bảng trung gian rồi DROP sau khi xong:**

| Bước | Bảng | Logic |
|------|------|-------|
| 1 | `material_stock` | PN_Infor hash-filtered |
| 2 | `backlog_orders` | backlog hash-filtered |
| 3 | `asn_raw` | ASN tương lai hash-filtered |
| 4 | `asn_agg` | Gom ASN theo `(marc_bbm_id, logsys, matnr, werks, gr_date_planned)` |
| 5 | `transit_time` | MAX(TT) per material |
| 6 | `all_days` | Cross: factory_calendar × material_stock × plant (mỗi vật liệu × mỗi ngày) |
| 7 | `consumption` | Gom backlog theo ngày |
| 8 | `backlog` | MAX backlog tích lũy đến hôm nay per material |
| 9 | `asn_planned_availability` | ASN qty dời sang planned_availability_date (gr_date + webaz) |
| 10 | `full_date_range` | all_days + ASN + stock + consumption + backlog |

**Công thức tồn kho mô phỏng:**
```sql
simulated_inventory_qty =
    available_stock                                                         -- tồn kho hiện tại
    - SUM(backlog)     OVER (PARTITION BY marc_bbm_id ORDER BY date)       -- overdue demand
    - SUM(consumption) OVER (PARTITION BY marc_bbm_id ORDER BY date)       -- future demand
    + SUM(lfimg)       OVER (PARTITION BY marc_bbm_id ORDER BY date)       -- ASN inbound
```

> Khi `simulated_inventory_qty < 0` → ngày đó là **red day** (thiếu hàng)

---

### Layer 10 — End Tables (tính bởi Go)

Từ `inventory_simulation`, Go code (`end_table_inventory_simulation.go`) tính thêm:

| Field | Logic |
|-------|-------|
| `red_days` | Danh sách ngày `simulated_inventory_qty < 0` |
| `end_of_tt_gr` | Ngày cuối trong cửa sổ `transit_time + webaz` |
| `min_qty_in_tt_gr` | Tồn kho nhỏ nhất trong cửa sổ TT |
| `status` | `"Shortage"` / `"No Shortage"` |
| `forecastweekly` | Dự báo hàng tuần (nhóm theo Sunday) |

**3 variants:**
- `inventory_simulation` — có ASN
- `inventory_simulation_no_supply` — không có ASN (tình huống xấu nhất)
- `inventory_simulation_by_order` — theo từng PO

---

## Kỹ thuật quan trọng

### Hash Partitioning (parallel workers)
```sql
-- Setup: tạo 10 partitions
CREATE TABLE ... PARTITION BY HASH(marc_bbm_id);
CREATE TABLE ..._p0 PARTITION OF ... FOR VALUES WITH (MODULUS 10, REMAINDER 0);
...

-- Transform: mỗi worker xử lý 1 partition
INSERT INTO ... WHERE abs(hashtext(marc_bbm_id::text) % $1) = $2
--  $1 = 10 (modulus), $2 = 0..9 (remainder)
```

### Staging Schema Pattern
```sql
CREATE SCHEMA staging_xyz;
-- ... tạo bảng trung gian có INDEX ...
INSERT INTO dali_prod_data.target ...;
DROP SCHEMA staging_xyz CASCADE;
```

### Date Arithmetic (N working days)
```sql
-- Cách 1: dùng working_calendar (historical)
JOIN working_calendar wc  ON calendar_dt = start_date AND logsys = X AND ident = fabkl
JOIN working_calendar wc2 ON working_day_index = wc.working_day_index + N AND ...

-- Cách 2: dùng factory_calendar_inventory_simulation (tương lai có jump_to_wd)
JOIN fc wc  ON calendar_dt = gr_date AND ...
JOIN fc wc2 ON technical_day_number = wc.technical_day_number
                + (CASE WHEN wc.is_workingday = 0 THEN 1 ELSE 0 END)
                + webaz
             AND is_workingday = 1
-- Kết quả: wc2.jump_to_wd_date
```

### Overdue / Null Row Pattern
Khi vật liệu có backlog quá hạn nhưng không có kế hoạch tương lai → tạo row `NULL date` để UI hiển thị:
```sql
UNION ALL
SELECT ..., NULL AS planned_date, SUM(overdue_qty) AS total_due
WHERE NOT EXISTS (SELECT 1 FROM ... WHERE date >= TODAY AND same_id)
```

---

## Surrogate Key Convention

| Key | Format | Ý nghĩa |
|-----|--------|---------|
| `marc_bbm_id` | `logsys-matnr-werks` | Material × Plant |
| `ekpo_bbm_id` | `logsys-ebeln-ebelp` | PO line |
| `lfa1_bbm_id` | `logsys-lifnr` | Vendor |
| `t001w_bbm_id` | `logsys-werks` | Plant |
| `qunum_j` | `logsys-qunum` | Quota arrangement |
| `saf_id` | `matnr-werks-logsys-ebeln-lifnr` | Scheduling agreement future |
| `plant_sys` | `logsys-werks` | alias cho t001w_bbm_id |

---

## SAP Table Mapping

| SAP Table | PostgreSQL raw | Nội dung |
|-----------|---------------|---------|
| MARC | `marc` | Material × Plant planning data |
| MARD | `mard` | Stock by storage location |
| EKET | `eket` | SA delivery schedule lines |
| EKKO | `ekko` | PO / SA header |
| EKPO | `ekpo` | PO / SA line items |
| VBBE | `vbbe` | Sales order stock requirements |
| RESB | `resb` | Production order requirements |
| LIKP | `likp` | Inbound delivery header |
| VBUP (LIPS) | `vbup_lips` | Delivery item statuses |
| RB04 | `rb04` | Transit time master (custom) |
| LFA1 | `lfa1` | Vendor master |
| T001W | `t001w` | Plant / factory calendar key |
| EQUK | `equk` | Quota arrangement header |
| EQUP | `equp` | Quota arrangement items |
| FAC_CALENDER | `fac_calender` | Factory calendar (custom) |
| BOM_PARENT_CHILD | `bom_parent_child` | BOM structure |
