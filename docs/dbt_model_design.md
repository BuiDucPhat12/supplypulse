# dbt Model Design — SupplyPulse

> Map từ Production DALI (`PRODUCTION_LOGIC.md`) sang dbt models của SupplyPulse.
> Dùng làm blueprint trước khi viết SQL.

---

## Cấu trúc thư mục đề xuất

```
supplypulse_dbt/
├── seeds/
│   └── seed_transit_time.csv          ← thay thế rb04 (xem Gaps bên dưới)
└── models/
    ├── staging/                        schema: staging  | materialized: view
    │   ├── sources.yml
    │   ├── stg_marc.sql
    │   ├── stg_mard.sql
    │   ├── stg_ekko.sql
    │   ├── stg_ekpo.sql
    │   ├── stg_eket.sql
    │   ├── stg_equk.sql
    │   ├── stg_equp.sql
    │   ├── stg_vbbe.sql                ← ⚠️ CẦN FIX (schema cũ)
    │   ├── stg_resb.sql
    │   ├── stg_likp.sql
    │   ├── stg_lips.sql
    │   ├── stg_vbup.sql
    │   ├── stg_lfa1.sql
    │   ├── stg_t001w.sql
    │   └── stg_tfact.sql               ← chỉ có tên lịch, không có is_workingday
    ├── intermediate/                   schema: intermediate | materialized: table
    │   ├── int_factory_calendar.sql    ← L2: generate_series thay fac_calender
    │   ├── int_working_calendar.sql    ← L2: filter is_workingday + row_number
    │   ├── int_material_bbm.sql        ← L1: surrogate key marc_bbm_id
    │   ├── int_pn_infor.sql            ← L1: marc + mard → stock + planning params
    │   ├── int_equk_active.sql         ← L3: dedup quota header
    │   ├── int_equp_active.sql         ← L3: dedup quota items
    │   ├── int_valid_quote_agreements.sql  ← L3: quota % per vendor
    │   ├── int_transit_time.sql        ← L3: từ seed_transit_time (thay rb04)
    │   ├── int_purchasing_document_active.sql  ← L4: ekko + ekpo + marc
    │   ├── int_purchasing_document_tt.sql      ← L4: + TT + quota %
    │   ├── int_backlog.sql             ← L5: resb UNION vbbe
    │   ├── int_sa_by_delivery_date.sql ← L6: gom eket theo eindt
    │   ├── int_scheduling_agreement.sql        ← L6: + PO header
    │   ├── int_sa_future.sql           ← L6: filter omenge != 0 + planned_availability_date
    │   ├── int_sa_late_shipment.sql    ← L6: late shipment flag 120 ngày
    │   ├── int_inbound_deliveries.sql  ← L7: likp + lips + vbup + marc
    │   ├── int_inbound_deliveries_asn.sql  ← L7: + planned_availability_date + ASN due
    │   ├── int_supply.sql              ← L8: Order Qty UNION ASN
    │   ├── int_tt_quota.sql            ← L8: TT + quota % per material/vendor/mmsa
    │   ├── int_partial_detail_supply.sql   ← L8: pn_infor × tt_quota × supply × calendar
    │   └── int_fill_missing_dates_supply.sql   ← L8: bù ngày thiếu trong 120 ngày
    └── marts/                          schema: analytics | materialized: table
        ├── mart_detail_supply.sql      ← L8 final: partial UNION fill
        ├── mart_inventory_simulation.sql   ← L9: tồn kho theo ngày
        ├── mart_consumption.sql        ← L10: nhu cầu theo ngày
        └── mart_shortage_report.sql    ← L10: red_days + status (thay Go code)
```

---

## Mapping đầy đủ: Production → dbt

### Staging Layer (1-1 với bronze tables)

| Bronze Table | dbt Model | Columns cần rename/cast | Status |
|---|---|---|---|
| MARC | `stg_marc` | `marc_bbm_id` = `logsys\|\|'-'\|\|matnr\|\|'-'\|\|werks` | missing |
| MARD | `stg_mard` | cast LABST/KLABS/SPEME/INSME sang numeric | missing |
| EKKO | `stg_ekko` | ebeln, lifnr, ekorg, logsys | missing |
| EKPO | `stg_ekpo` | `ekpo_bbm_id` = `logsys\|\|'-'\|\|ebeln\|\|'-'\|\|ebelp` | missing |
| EKET | `stg_eket` | eindt → date, menge/wemng/omenge → numeric | missing |
| EQUK | `stg_equk` | vdatu/bdatu → date | missing |
| EQUP | `stg_equp` | quote → numeric | missing |
| VBBE | `stg_vbbe` | **FIX:** dùng MBDAT/OMENG/VMENG/BDART/AUART/KUNNR | **⚠️ BROKEN** |
| RESB | `stg_resb` | bdter → date, bdmng → numeric | missing |
| LIKP | `stg_likp` | lfdat/erdat/wadat_ist → date | missing |
| LIPS | `stg_lips` | lfimg → numeric | missing |
| VBUP | `stg_vbup` | wbsta (GR status) | exists |
| LFA1 | `stg_lfa1` | `lfa1_bbm_id` = `logsys\|\|'-'\|\|lifnr` | missing |
| T001W | `stg_t001w` | werks, fabkl (factory calendar key) | missing |
| TFACT | `stg_tfact` | ident, ltext (tên lịch) | missing |

### Intermediate Layer

| Production Layer | Production Table | dbt Model | Sources | Notes |
|---|---|---|---|---|
| L2 | `fac_calender` | `int_factory_calendar` | `stg_t001w` + `generate_series` | Generate ngày từ today → today+180 ngày, join T001W để lấy fabkl. `is_workingday` dựa trên thứ (Mon-Fri = 1) — đơn giản hóa so production |
| L2 | `working_calendar` | `int_working_calendar` | `int_factory_calendar` | Filter `is_workingday=1` + ROW_NUMBER() → `working_day_index` |
| L1 | `material_bbm` | `int_material_bbm` | `stg_marc` | surrogate key `marc_bbm_id` |
| L1 | `PN_Infor` | `int_pn_infor` | `stg_marc` + `stg_mard` | Window SUM stock, planning params (webaz, eisbe, shzet, fxhor, beskz, dispo) |
| L3 | `equk_bbm_active` | `int_equk_active` | `stg_equk` | ROW_NUMBER() dedup, filter CURRENT_DATE BETWEEN vdatu AND bdatu |
| L3 | `equp_bbm_active` | `int_equp_active` | `stg_equp` | ROW_NUMBER() dedup |
| L3 | `valid_quote_agreements` | `int_valid_quote_agreements` | `int_equk_active` + `int_equp_active` + `stg_lfa1` | `quote_percent = quote / SUM(quote) OVER (PARTITION BY qunum)` |
| L3 | `rb04_yl1_ediwkn_bbm_active` | `int_transit_time` | `seed_transit_time` | Join seed với stg_lfa1 + stg_t001w |
| L4 | `purchasing_document_active` | `int_purchasing_document_active` | `stg_ekko` + `stg_ekpo` + `stg_marc` | Filter loekz NOT IN ('L','S','X') |
| L4 | `purchasing_document_transit_time` | `int_purchasing_document_tt` | `int_purchasing_document_active` + `int_transit_time` + `int_valid_quote_agreements` | TT + quota % per PO line |
| L5 | `backlog` | `int_backlog` | `stg_resb` + `stg_vbbe` | UNION ALL resb + vbbe, tính backlog_per_pn (overdue), null row pattern |
| L6 | `scheduling_agreement_by_delivery_date` | `int_sa_by_delivery_date` | `stg_eket` | GROUP BY ekpo_bbm_id + eindt, SUM menge/wemng/omenge |
| L6 | `scheduling_agreement` | `int_scheduling_agreement` | `int_purchasing_document_active` + `int_sa_by_delivery_date` | JOIN on ekpo_bbm_id |
| L6 | `scheduling_agreement_future` | `int_sa_future` | `int_scheduling_agreement` + `int_working_calendar` + `stg_lfa1` + `int_valid_quote_agreements` | `planned_availability_date = eindt + webaz working days` |
| L6 | `scheduling_agreement_late_shipment` | `int_sa_late_shipment` | `int_sa_future` + `int_inbound_deliveries_asn` | 120-day window, late_shipment_flag |
| L7 | `inbound_deliveries` | `int_inbound_deliveries` | `stg_likp` + `stg_lips` + `stg_vbup` + `stg_marc` | `budat_mkpf = MIN(erdat, wadat_ist)` |
| L7 | `inbound_deliveries_asn` | `int_inbound_deliveries_asn` | `int_inbound_deliveries` + `int_working_calendar` + `stg_lfa1` + `int_valid_quote_agreements` | Filter vbup.wbsta != 'C', 3 loại output (future/overdue/completed) |
| L8 | `supply` | `int_supply` | `int_sa_late_shipment` + `int_inbound_deliveries_asn` | UNION ALL Order Qty + ASN |
| L8 | `TT_Quota` | `int_tt_quota` | `stg_marc` + `int_purchasing_document_active` + `stg_lfa1` + `int_valid_quote_agreements` + `int_transit_time` | MAX_TT per material |
| L8 | `partial_detail_supply` | `int_partial_detail_supply` | `int_pn_infor` + `int_tt_quota` + `int_supply` + `int_factory_calendar` | pn_infor × tt_quota × supply × calendar (mỗi material × vendor × mmsa × ngày) |
| L8 | `fill_missing_dates_supply` | `int_fill_missing_dates_supply` | `int_partial_detail_supply` + `int_factory_calendar` | Bù ngày thiếu (qty=0) trong 120 ngày |

### Marts Layer

| Production Layer | Production Table | dbt Model | Sources | Notes |
|---|---|---|---|---|
| L8 final | `final_detail_supply` | `mart_detail_supply` | `int_partial_detail_supply` + `int_fill_missing_dates_supply` | UNION ALL |
| L9 | `inventory_simulation` | `mart_inventory_simulation` | `int_pn_infor` + `int_backlog` + `int_inbound_deliveries_asn` + `int_factory_calendar` + `int_purchasing_document_tt` + `stg_t001w` | Công thức: `available_stock - SUM(backlog) - SUM(consumption) + SUM(lfimg)` OVER date |
| L10 | `Consumption` | `mart_consumption` | `stg_marc` + `int_backlog` | Group backlog theo ngày |
| L10 | `inventory_simulation` (end) | `mart_shortage_report` | `mart_inventory_simulation` | Thay Go code: tính red_days, min_qty_in_tt_gr, status = "Shortage"/"No Shortage" trong SQL |

---

## Gaps & Adaptations

### Gap 1: `rb04` (Transit Time Master) — CRITICAL
- **Production:** Custom SAP table `rb04` với cột `rb04_yl1_transt` (transit time ngày) per vendor/route
- **SupplyPulse:** Không có bảng này
- **Giải pháp:** Tạo dbt seed `seeds/seed_transit_time.csv` với schema:

```
logsys, ekorg, werks, lifnr, evers, transit_time_days, fabkl
```

Điền giá trị synthetic (5–30 ngày tùy vendor).

### Gap 2: `fac_calender` (Factory Calendar) — CRITICAL
- **Production:** Custom table, mỗi row = 1 ngày, có cột `is_workingday`
- **SupplyPulse:** `TFACT` chỉ có `IDENT` + `LTEXT` (tên lịch), không có daily data
- **Giải pháp:** `int_factory_calendar` dùng PostgreSQL `generate_series`:
  ```sql
  -- Sinh ngày từ today đến today + 180 ngày
  -- is_workingday = CASE WHEN EXTRACT(DOW FROM d) NOT IN (0,6) THEN 1 ELSE 0 END
  -- Đơn giản hóa: bỏ qua ngày lễ. Đủ để demo inventory simulation.
  ```

### Gap 3: `bom_parent_child` — NON-CRITICAL
- **Production:** BOM traversal cho L10 `pn_next_level`
- **SupplyPulse:** Không có bảng BOM
- **Giải pháp:** Bỏ qua. Tạo `mart_shortage_report` không có BOM traversal. Phase 5+ có thể thêm.

### Gap 4: `vbup_lips` — MINOR
- **Production:** Joined table (VBUP + LIPS merged)
- **SupplyPulse:** Có `VBUP` + `LIPS` riêng lẻ trong bronze
- **Giải pháp:** JOIN trong `int_inbound_deliveries` — không cần model riêng.

### Không dùng từ bronze
Các bảng trong bronze nhưng không có trong DALI pipeline: `VBAK`, `VBAP`, `KNA1`, `MARA`.
Sẽ dùng sau cho Order-to-Cash analytics (Phase 4+), không liên quan inventory simulation.

---

## Build Order (thứ tự chạy dbt)

```
Phase A — Staging (fix + tạo mới)
  1. FIX stg_vbbe
  2. stg_marc, stg_mard
  3. stg_ekko, stg_ekpo, stg_eket
  4. stg_equk, stg_equp
  5. stg_resb
  6. stg_likp, stg_lips (stg_vbup đã có)
  7. stg_lfa1, stg_t001w, stg_tfact

Phase B — Foundations (không phụ thuộc calendar hoặc rb04)
  8. seed_transit_time
  9. int_material_bbm
  10. int_pn_infor
  11. int_backlog
  12. int_purchasing_document_active
  13. int_equk_active, int_equp_active, int_valid_quote_agreements
  14. int_transit_time (từ seed)

Phase C — Calendar (unblock phần còn lại)
  15. int_factory_calendar    ← generate_series
  16. int_working_calendar

Phase D — PO + SA + ASN
  17. int_purchasing_document_tt
  18. int_sa_by_delivery_date
  19. int_scheduling_agreement
  20. int_inbound_deliveries

Phase E — Future Supply & ASN (phụ thuộc calendar)
  21. int_sa_future
  22. int_inbound_deliveries_asn
  23. int_sa_late_shipment

Phase F — Supply Consolidation
  24. int_tt_quota
  25. int_supply
  26. int_partial_detail_supply
  27. int_fill_missing_dates_supply

Phase G — Marts
  28. mart_detail_supply
  29. mart_inventory_simulation
  30. mart_consumption
  31. mart_shortage_report
```

---

## Immediate Next Steps

1. **Fix `stg_vbbe.sql`** — đổi cột sang schema mới (MBDAT, OMENG, VMENG, BDART, AUART, KUNNR)
2. **Thêm `intermediate/` và `marts/` vào `dbt_project.yml`** — materialization + schema config
3. **Viết Phase A** — toàn bộ staging models còn thiếu (13 models)
4. **Tạo `seed_transit_time.csv`** — giải quyết Gap 1 (rb04)
5. **Viết `int_factory_calendar.sql`** — giải quyết Gap 2 (fac_calender)
6. **Viết `int_pn_infor.sql`** và `int_backlog.sql` — core logic, không blocked

---

## Self-check trước khi code

Trả lời được 3 câu này trước khi bắt đầu viết mỗi model:

1. **Nguồn:** Model này `ref()` hoặc `source()` từ đâu?
2. **Grain:** Mỗi row đại diện cho cái gì? (1 material? 1 material × 1 ngày? 1 PO line?)
3. **Key:** Surrogate key hoặc natural key là gì?
