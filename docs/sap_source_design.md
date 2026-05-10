# SAP SE16 Source Design

> **Owner:** Bui Duc
> **Status:** DRAFT — bạn tự điền các phần `<...>` bên dưới.
> **Mục đích:** trước khi viết bất kỳ dòng code nào, chốt rõ source: bảng nào, field nào, volume bao nhiêu, refresh ra sao.

---

## 0. Quyết định scope

**Module SAP focus** *(tick những module bạn sẽ dùng)*:

- [x] **SD** — Sales & Distribution (sales order, delivery, billing)
- [x] **MM** — Materials Management (purchase order, GR, vendor)
- [ ] **PP** — Production Planning (production order, BOM, routing)
- [ ] **WM/EWM** — Warehouse Management (stock movement, bin)
- [ ] **FI/CO** — Finance / Controlling (chỉ nếu thực sự cần)

**Lý do chọn:**

```
SD + MM bao trọn 2 vòng nghiệp vụ cốt lõi của chuỗi cung ứng:
- SD (Order-to-Cash): từ lúc khách hàng đặt hàng → giao hàng → xuất hóa đơn.
- MM (Procure-to-Pay): từ lúc tạo PO với nhà cung cấp → nhận hàng (GR) → thanh toán.
Hai module này cung cấp đủ signal để làm: demand forecast, supplier OTD, SLA risk scoring, inventory health.
PP để lại Phase sau khi SD+MM pipeline đã ổn định.
```

---

## 1. Danh sách bảng SE16

Điền theo template; xoá dòng không dùng, thêm dòng mới nếu cần.

### 1.1 Sales & Distribution (SD)

| Table | Tên đầy đủ            | Loại     | Key                | Volume ước tính | Refresh | Ghi chú |
| ----- | --------------------- | -------- | ------------------ | --------------- | ------- | ------- |
| VBAK  | Sales Order Header    | TX (fact)| VBELN              | ~500/day        | hourly  | Mỗi VBELN = 1 order header |
| VBAP  | Sales Order Item      | TX       | VBELN, POSNR       | ~2000/day       | hourly  | ~4 item/order trung bình |
| LIKP  | Delivery Header       | TX       | VBELN              | ~400/day        | hourly  | VBELN ở đây là delivery doc |
| LIPS  | Delivery Item         | TX       | VBELN, POSNR       | ~1600/day       | hourly  | |
| VBFA  | Document Flow         | TX       | VBELV, VBELN, POSNN| ~3000/day       | hourly  | Trace chuỗi order→delivery→invoice |
| VBUP  | Sales Doc Item Status | TX       | VBELN, POSNR       | ~2000/day       | hourly  | Status per item: goods mvmt, billing, picking |
| VBBE  | Sales Requirements    | TX       | MATNR, WERKS, VBELN, POSNR | ~2000/day | hourly | Open sales requirements fed into MRP/ATP |
| KNA1  | Customer Master       | MD (dim) | KUNNR              | small (~5K rows)| daily   | PII: NAME1, ORT01 cần mask |

### 1.2 Materials Management (MM)

| Table | Tên đầy đủ           | Loại | Key                    | Volume ước tính | Refresh | Ghi chú          |
| ----- | -------------------- | ---- | ---------------------- | --------------- | ------- | ---------------- |
| EKKO  | PO Header            | TX   | EBELN                  | ~200/day        | hourly  | |
| EKPO  | PO Item              | TX   | EBELN, EBELP           | ~600/day        | hourly  | |
| EKET  | PO Schedule Line     | TX   | EBELN, EBELP, ETENR    | ~600/day        | hourly  | Key cho lead time calculation |
| EQUK  | Quota Arrangement Header | MD | MATNR, WERKS          | small           | daily   | Quota validity window per material-plant |
| EQUP  | Quota Arrangement Item   | MD | QUNUM, QUPOS          | small           | daily   | Vendor split % + min/max qty per quota item |
| MKPF  | Material Doc Header  | TX   | MBLNR, MJAHR           | ~300/day        | hourly  | Header của GR/GI movement |
| MSEG  | Material Doc Item    | TX   | MBLNR, MJAHR, ZEILE    | ~900/day        | hourly  | Chi tiết từng material movement |
| MARA  | Material Master (client)  | MD | MATNR               | small (~50K rows)| daily  | Global material attributes |
| MARC  | Material Plant Data  | MD   | MATNR, WERKS           | medium          | daily   | Attributes theo plant (MRP, lot size) |
| MARD  | Storage Loc Stock    | MD   | MATNR, WERKS, LGORT    | medium          | hourly  | Inventory snapshot per storage loc |
| LFA1  | Vendor Master        | MD   | LIFNR                  | small (~3K rows)| daily   | PII: NAME1, ORT01 cần mask |
| RESB  | Reservation/Dep. Req | TX   | RSNUM, RSPOS           | ~500/day        | hourly  | Material reservations; links sales orders → stock commit |

> **Volume trên là ước tính mẫu.** Với Bosch production: VBAP/MSEG thường lớn hơn nhiều (có thể 50K-500K/day). Điền lại khi bạn có số thực tế.

### 1.3 Organisation & Configuration Data

| Table  | Tên đầy đủ            | Loại        | Key   | Volume       | Refresh | Ghi chú |
| ------ | --------------------- | ----------- | ----- | ------------ | ------- | ------- |
| T001W  | Plant / Branch        | CFG (config)| WERKS         | small (~100) | weekly  | Org master — plant name, country, factory calendar key |
| TFACT  | Factory Calendar Texts| CFG (config)| IDENT, SPRAS  | tiny         | static  | Human-readable label for each factory calendar ID |

### 1.4 Production Planning (PP) — KHÔNG dùng ở Phase 1

> Loại khỏi scope. Ghi chú để sau: AUFK, AFKO, AFPO sẽ thêm khi SD+MM pipeline ổn định.

---

## 2. Field-level design (chi tiết bảng quan trọng)

**Quy tắc đặt tên ở Silver:** `snake_case`, không giữ tên SAP gốc; đổi sang English business chuẩn. PII fields phải hash (SHA-256) hoặc faker-replace trước khi rời Bronze.

### VBAK — Sales Order Header

| Field   | SAP type | Business meaning                  | Bronze keep? | Silver name        | PII? |
| ------- | -------- | --------------------------------- | ------------ | ------------------ | ---- |
| MANDT   | CLNT     | Client                            | no           | —                  | no   |
| VBELN   | CHAR(10) | Sales order number                | yes          | sales_order_id     | no   |
| ERDAT   | DATS     | Order created date                | yes          | created_date       | no   |
| ERZET   | TIMS     | Order created time                | yes          | created_time       | no   |
| ERNAM   | CHAR(12) | Created by (SAP user)             | yes          | created_by_user    | yes  |
| AUART   | CHAR(4)  | Sales document type (OR/ZOR/...)  | yes          | order_type_code    | no   |
| KUNNR   | CHAR(10) | Sold-to customer number           | yes          | customer_id        | semi |
| NETWR   | CURR(15) | Net value of order                | yes          | net_value          | no   |
| WAERK   | CUKY(5)  | Document currency                 | yes          | currency_code      | no   |
| VKORG   | CHAR(4)  | Sales organization                | yes          | sales_org_id       | no   |
| VTWEG   | CHAR(2)  | Distribution channel              | yes          | distribution_channel| no  |
| SPART   | CHAR(2)  | Division                          | yes          | division_code      | no   |
| GBSTK   | CHAR(1)  | Overall processing status         | yes          | order_status       | no   |

### VBAP — Sales Order Item

| Field   | SAP type | Business meaning                  | Bronze keep? | Silver name        | PII? |
| ------- | -------- | --------------------------------- | ------------ | ------------------ | ---- |
| VBELN   | CHAR(10) | Sales order number (FK → VBAK)    | yes          | sales_order_id     | no   |
| POSNR   | NUMC(6)  | Item number                       | yes          | item_number        | no   |
| MATNR   | CHAR(18) | Material number (FK → MARA)       | yes          | material_id        | no   |
| MATKL   | CHAR(9)  | Material group (FK → MARA.MATKL)  | yes          | material_group     | no   |
| MENGE   | QUAN     | Order quantity                    | yes          | ordered_qty        | no   |
| MEINS   | UNIT(3)  | Base unit of measure              | yes          | uom                | no   |
| NETWR   | CURR     | Net value of item                 | yes          | net_value          | no   |
| WAERK   | CUKY     | Document currency                 | yes          | currency_code      | no   |
| WERKS   | CHAR(4)  | Plant                             | yes          | plant_id           | no   |
| LGORT   | CHAR(4)  | Storage location                  | yes          | storage_location_id| no   |
| PSTYV   | CHAR(4)  | Item category (TAN/TANN/...)      | yes          | item_category_code | no   |
| ABGRU   | CHAR(2)  | Rejection reason code             | yes          | rejection_reason   | no   |
| ERDAT   | DATS     | Item creation date                | yes          | created_date       | no   |

### LIKP — Delivery Header

| Field      | SAP type  | Business meaning                         | Bronze keep? | Silver name           | PII? |
| ---------- | --------- | ---------------------------------------- | ------------ | --------------------- | ---- |
| VBELN      | CHAR(10)  | Delivery document number (PK)            | yes          | delivery_id           | no   |
| LFART      | CHAR(4)   | Delivery type (LF/LFRE/...)              | yes          | delivery_type         | no   |
| BLDAT      | DATS      | Document date                            | yes          | doc_date              | no   |
| WADAT      | DATS      | Planned goods issue date                 | yes          | planned_gi_date       | no   |
| WADAT_IST  | DATS      | Actual goods issue date                  | yes          | actual_gi_date        | no   |
| KODAT      | DATS      | Picking date                             | yes          | picking_date          | no   |
| LADDT      | DATS      | Loading date                             | yes          | loading_date          | no   |
| TDDAT      | DATS      | Transportation planning date             | yes          | transport_plan_date   | no   |
| KUNNR      | CHAR(10)  | Ship-to party (FK → KNA1)                | yes          | ship_to_customer_id   | semi |
| KUNAG      | CHAR(10)  | Sold-to party (FK → KNA1)                | yes          | sold_to_customer_id   | semi |
| VKORG      | CHAR(4)   | Sales organization                       | yes          | sales_org_id          | no   |
| VSTEL      | CHAR(4)   | Shipping point                           | yes          | shipping_point_id     | no   |
| ROUTE      | CHAR(6)   | Route                                    | yes          | route_id              | no   |
| INCO1      | CHAR(3)   | Incoterms (EXW/DAP/CIF/...)              | yes          | incoterms             | no   |
| BTGEW      | QUAN      | Total weight                             | yes          | total_weight          | no   |
| GEWEI      | UNIT(3)   | Weight unit                              | yes          | weight_unit           | no   |

### LIPS — Delivery Item

| Field  | SAP type  | Business meaning                           | Bronze keep? | Silver name             | PII? |
| ------ | --------- | ------------------------------------------ | ------------ | ----------------------- | ---- |
| VBELN  | CHAR(10)  | Delivery number (FK → LIKP)                | yes          | delivery_id             | no   |
| POSNR  | NUMC(6)   | Delivery item number                       | yes          | delivery_item_number    | no   |
| MATNR  | CHAR(18)  | Material number (FK → MARA)                | yes          | material_id             | no   |
| ARKTX  | CHAR(40)  | Short description                          | no           | —                       | no   |
| LFIMG  | QUAN      | Actual delivery quantity                   | yes          | delivery_qty            | no   |
| LGMNG  | QUAN      | Picked quantity                            | yes          | picked_qty              | no   |
| VRKME  | UNIT(3)   | Sales unit                                 | yes          | sales_uom               | no   |
| WERKS  | CHAR(4)   | Plant                                      | yes          | plant_id                | no   |
| LGORT  | CHAR(4)   | Storage location                           | yes          | storage_location_id     | no   |
| CHARG  | CHAR(10)  | Batch number                               | yes          | batch_id                | no   |
| VGBEL  | CHAR(10)  | Source sales order (FK → VBAK)             | yes          | source_order_id         | no   |
| VGPOS  | NUMC(6)   | Source sales order item (FK → VBAP)        | yes          | source_order_item       | no   |
| WBSTA  | CHAR(1)   | Goods movement status                      | yes          | goods_movement_status   | no   |
| PSTYV  | CHAR(4)   | Item category                              | yes          | item_category_code      | no   |
| NTGEW  | QUAN      | Net weight                                 | yes          | net_weight              | no   |
| BRGEW  | QUAN      | Gross weight                               | yes          | gross_weight            | no   |

### VBUP — Sales Document Item Status

| Field  | SAP type | Business meaning                           | Bronze keep? | Silver name             | PII? |
| ------ | -------- | ------------------------------------------ | ------------ | ----------------------- | ---- |
| VBELN  | CHAR(10) | Sales document number (FK → VBAK)          | yes          | sales_order_id          | no   |
| POSNR  | NUMC(6)  | Item number (FK → VBAP)                    | yes          | item_number             | no   |
| GBSTA  | CHAR(1)  | Overall processing status (A/B/C)          | yes          | overall_status          | no   |
| ABSTK  | CHAR(1)  | Rejection status                           | yes          | rejection_status        | no   |
| WBSTK  | CHAR(1)  | Goods movement status                      | yes          | goods_movement_status   | no   |
| FKSTK  | CHAR(1)  | Billing / invoice status                   | yes          | billing_status          | no   |
| LVSTK  | CHAR(1)  | Picking status                             | yes          | picking_status          | no   |
| LSSTK  | CHAR(1)  | WM transfer order status                   | yes          | wm_activity_status      | no   |
| KOSTA  | CHAR(1)  | Cost status                                | yes          | cost_status             | no   |
| LFGSK  | CHAR(1)  | Overall delivery status                    | yes          | delivery_status         | no   |

### VBBE — Sales Requirements (Individual Customer Requirements)

> **Lưu ý:** VBBE không có field BDMNG (requirement qty). Quantity fields thực tế là OMENG (open qty) và VMENG (confirmed qty). Verified qua leanx.eu ECC tables.

| Field  | SAP type | Business meaning                           | Bronze keep? | Silver name             | PII? |
| ------ | -------- | ------------------------------------------ | ------------ | ----------------------- | ---- |
| VBELN  | CHAR(10) | Sales document (FK → VBAK)                 | yes          | sales_order_id          | no   |
| POSNR  | NUMC(6)  | Sales document item (FK → VBAP)            | yes          | item_number             | no   |
| MATNR  | CHAR(18) | Material number (FK → MARA)                | yes          | material_id             | no   |
| WERKS  | CHAR(4)  | Plant                                      | yes          | plant_id                | no   |
| MBDAT  | DATS     | Material staging / availability date       | yes          | availability_date       | no   |
| OMENG  | QUAN     | Open quantity (stock keeping units)        | yes          | open_qty                | no   |
| VMENG  | QUAN     | Confirmed quantity for availability check  | yes          | confirmed_qty           | no   |
| MEINS  | UNIT(3)  | Unit of measure                            | yes          | uom                     | no   |
| BDART  | CHAR(2)  | Requirements type (KE / KEL / ...)         | yes          | requirements_type       | no   |
| AUART  | CHAR(4)  | Sales document type (FK → VBAK.AUART)      | yes          | order_type_code         | no   |
| KUNNR  | CHAR(10) | Sold-to customer (FK → KNA1)               | yes          | customer_id             | semi |

### EKKO — Purchase Order Header

| Field   | SAP type | Business meaning                  | Bronze keep? | Silver name        | PII? |
| ------- | -------- | --------------------------------- | ------------ | ------------------ | ---- |
| EBELN   | CHAR(10) | PO number                         | yes          | po_id              | no   |
| BUKRS   | CHAR(4)  | Company code                      | yes          | company_code       | no   |
| BSART   | CHAR(4)  | PO type (NB/FO/...)               | yes          | po_type_code       | no   |
| LIFNR   | CHAR(10) | Vendor number (FK → LFA1)         | yes          | vendor_id          | no   |
| EKORG   | CHAR(4)  | Purchasing organization           | yes          | purchasing_org_id  | no   |
| EKGRP   | CHAR(3)  | Purchasing group                  | yes          | purchasing_group   | no   |
| BEDAT   | DATS     | PO date                           | yes          | po_date            | no   |
| WAERS   | CUKY     | Currency                          | yes          | currency_code      | no   |

### EKPO — Purchase Order Item

| Field   | SAP type | Business meaning                  | Bronze keep? | Silver name        | PII? |
| ------- | -------- | --------------------------------- | ------------ | ------------------ | ---- |
| EBELN   | CHAR(10) | PO number (FK → EKKO)             | yes          | po_id              | no   |
| EBELP   | NUMC(5)  | PO item number                    | yes          | po_item_number     | no   |
| MATNR   | CHAR(18) | Material number (FK → MARA)       | yes          | material_id        | no   |
| MENGE   | QUAN     | PO quantity                       | yes          | ordered_qty        | no   |
| MEINS   | UNIT     | Unit of measure                   | yes          | uom                | no   |
| NETPR   | CURR     | Net price                         | yes          | net_price          | no   |
| PEINH   | QUAN     | Price unit                        | yes          | price_unit         | no   |
| WERKS   | CHAR(4)  | Plant                             | yes          | plant_id           | no   |
| EINDT   | DATS     | Delivery date (from schedule line)| yes          | scheduled_delivery_date | no |
| ELIKZ   | CHAR(1)  | Delivery completed flag           | yes          | delivery_completed | no   |

### EKET — PO Schedule Line

| Field  | SAP type | Business meaning                           | Bronze keep? | Silver name               | PII? |
| ------ | -------- | ------------------------------------------ | ------------ | ------------------------- | ---- |
| EBELN  | CHAR(10) | PO number (FK → EKKO)                      | yes          | po_id                     | no   |
| EBELP  | NUMC(5)  | PO item number (FK → EKPO)                 | yes          | po_item_number            | no   |
| ETENR  | NUMC(4)  | Schedule line number                       | yes          | schedule_line_number      | no   |
| EINDT  | DATS     | Scheduled delivery date (promised by vendor)| yes         | scheduled_delivery_date   | no   |
| SLFDT  | DATS     | Statistics-relevant delivery date          | yes          | stats_delivery_date       | no   |
| MENGE  | QUAN     | Schedule line quantity                     | yes          | scheduled_qty             | no   |
| WEMNG  | QUAN     | GR quantity for this schedule line         | yes          | gr_qty                    | no   |
| WEDAT  | DATS     | Date of last goods receipt                 | yes          | last_gr_date              | no   |
| GLMNG  | QUAN     | Open quantity still to be delivered        | yes          | open_delivery_qty         | no   |
| BANFN  | CHAR(10) | Purchase requisition                       | yes          | pr_id                     | no   |
| BNFPO  | NUMC(5)  | PR item number                             | yes          | pr_item_number            | no   |

### MARA — Material Master (client-level)

| Field   | SAP type  | Business meaning                  | Bronze keep? | Silver name        | PII? |
| ------- | --------- | --------------------------------- | ------------ | ------------------ | ---- |
| MATNR   | CHAR(18)  | Material number (PK)              | yes          | material_id        | no   |
| MTART   | CHAR(4)   | Material type (ROH/FERT/HALB/...) | yes          | material_type_code | no   |
| MBRSH   | CHAR(1)   | Industry sector                   | yes          | industry_sector    | no   |
| MATKL   | CHAR(9)   | Material group                    | yes          | material_group     | no   |
| MEINS   | UNIT(3)   | Base unit of measure              | yes          | base_uom           | no   |
| BRGEW   | QUAN      | Gross weight                      | yes          | gross_weight       | no   |
| GEWEI   | UNIT(3)   | Weight unit                       | yes          | weight_unit        | no   |
| ERSDA   | DATS      | Created on                        | yes          | created_date       | no   |

### EQUK — Quota Arrangement Header

| Field  | SAP type  | Business meaning                              | Bronze keep? | Silver name              | PII? |
| ------ | --------- | --------------------------------------------- | ------------ | ------------------------ | ---- |
| MATNR  | CHAR(18)  | Material number (FK → MARA)                   | yes          | material_id              | no   |
| WERKS  | CHAR(4)   | Plant (FK → T001W)                            | yes          | plant_id                 | no   |
| QUNUM  | CHAR(10)  | Quota arrangement number                      | yes          | quota_id                 | no   |
| VDATU  | DATS      | Valid from date                               | yes          | valid_from               | no   |
| BDATU  | DATS      | Valid until date                              | yes          | valid_to                 | no   |
| SCMNG  | QUAN(15)  | Minimum splitting quantity                    | yes          | min_split_qty            | no   |
| ERDAT  | DATS      | Created on                                    | yes          | created_date             | no   |
| ERNAM  | CHAR(12)  | Created by                                    | yes          | created_by_user          | yes  |

### EQUP — Quota Arrangement Item

| Field  | SAP type | Business meaning                              | Bronze keep? | Silver name              | PII? |
| ------ | -------- | --------------------------------------------- | ------------ | ------------------------ | ---- |
| QUNUM  | CHAR(10) | Quota arrangement number (FK → EQUK)          | yes          | quota_id                 | no   |
| QUPOS  | NUMC(3)  | Quota arrangement item                        | yes          | quota_item               | no   |
| BESKZ  | CHAR(1)  | Procurement type (E=external, F=in-house)     | yes          | procurement_type         | no   |
| LIFNR  | CHAR(10) | Vendor account number (FK → LFA1)             | yes          | vendor_id                | no   |
| BEWRK  | CHAR(4)  | Supplying plant (FK → T001W)                  | yes          | supplying_plant_id       | no   |
| QUOTE  | DEC(5)   | Quota percentage for this vendor/source       | yes          | quota_pct                | no   |
| QUBMG  | QUAN     | Quota base quantity                           | yes          | quota_base_qty           | no   |
| QUMNG  | QUAN     | Allocated quantity (consumed against quota)   | yes          | allocated_qty            | no   |
| MAXMG  | QUAN     | Maximum quantity per quota item               | yes          | max_qty                  | no   |
| MINLS  | QUAN     | Minimum lot size                              | yes          | min_lot_size             | no   |
| MAXLS  | QUAN     | Maximum lot size                              | yes          | max_lot_size             | no   |
| PLIFZ  | DEC(3)   | Planned delivery time in days                 | yes          | planned_delivery_days    | no   |
| PREIH  | NUMC(2)  | Priority for source sequence                  | yes          | source_priority          | no   |
| VERID  | CHAR(4)  | Production version                            | yes          | production_version       | no   |

### TFACT — Factory Calendar Texts

| Field  | SAP type | Business meaning                              | Bronze keep? | Silver name              | PII? |
| ------ | -------- | --------------------------------------------- | ------------ | ------------------------ | ---- |
| IDENT  | CHAR(2)  | Factory calendar ID (FK → T001W.FABKL)        | yes          | factory_calendar_id      | no   |
| SPRAS  | LANG(1)  | Language key                                  | yes          | language_key             | no   |
| LTEXT  | CHAR(60) | Calendar description text                     | yes          | calendar_description     | no   |

### RESB — Reservation / Dependent Requirements

| Field  | SAP type  | Business meaning                           | Bronze keep? | Silver name             | PII? |
| ------ | --------- | ------------------------------------------ | ------------ | ----------------------- | ---- |
| RSNUM  | NUMC(10)  | Reservation number                         | yes          | reservation_id          | no   |
| RSPOS  | NUMC(4)   | Reservation item                           | yes          | reservation_item        | no   |
| RSART  | CHAR(1)   | Reservation type (M=matdoc, F=prod order)  | yes          | reservation_type        | no   |
| MATNR  | CHAR(18)  | Material number (FK → MARA)                | yes          | material_id             | no   |
| WERKS  | CHAR(4)   | Plant                                      | yes          | plant_id                | no   |
| LGORT  | CHAR(4)   | Storage location                           | yes          | storage_location_id     | no   |
| BDMNG  | QUAN      | Required quantity                          | yes          | required_qty            | no   |
| ENMNG  | QUAN      | Quantity already withdrawn                 | yes          | withdrawn_qty           | no   |
| MEINS  | UNIT(3)   | Unit of measure                            | yes          | uom                     | no   |
| BDDAT  | DATS      | Requirement date                           | yes          | requirements_date       | no   |
| AUFNR  | CHAR(12)  | Production / process order (FK → AUFK)     | yes          | production_order_id     | no   |
| VBELN  | CHAR(10)  | Sales order reference (FK → VBAK)          | yes          | sales_order_id          | no   |
| KZEAR  | CHAR(1)   | Final issue indicator                      | yes          | final_issue_flag        | no   |

### LFA1 — Vendor Master

| Field  | SAP type  | Business meaning                           | Bronze keep? | Silver name             | PII? |
| ------ | --------- | ------------------------------------------ | ------------ | ----------------------- | ---- |
| LIFNR  | CHAR(10)  | Vendor number (PK)                         | yes          | vendor_id               | no   |
| LAND1  | CHAR(3)   | Country key                                | yes          | country_code            | no   |
| NAME1  | CHAR(35)  | Vendor name                                | yes          | vendor_name             | yes  |
| ORT01  | CHAR(35)  | City                                       | yes          | city                    | semi |
| PSTLZ  | CHAR(10)  | Postal code                                | yes          | postal_code             | semi |
| REGIO  | CHAR(3)   | Region / state                             | yes          | region_code             | no   |
| KTOKK  | CHAR(4)   | Vendor account group                       | yes          | account_group           | no   |
| STCD1  | CHAR(16)  | Tax number 1                               | yes          | tax_id                  | yes  |
| ERDAT  | DATS      | Created on                                 | yes          | created_date            | no   |
| ERNAM  | CHAR(12)  | Created by (SAP user)                      | yes          | created_by_user         | yes  |
| SPERR  | CHAR(1)   | Central posting block                      | yes          | posting_blocked         | no   |
| XCPDK  | CHAR(1)   | One-time account indicator                 | yes          | one_time_flag           | no   |

### T001W — Plant / Branch

| Field  | SAP type  | Business meaning                                  | Bronze keep? | Silver name               | PII? |
| ------ | --------- | ------------------------------------------------- | ------------ | ------------------------- | ---- |
| WERKS  | CHAR(4)   | Plant key (PK)                                    | yes          | plant_id                  | no   |
| NAME1  | CHAR(30)  | Plant name                                        | yes          | plant_name                | no   |
| BWKEY  | CHAR(4)   | Valuation area                                    | yes          | valuation_area            | no   |
| LAND1  | CHAR(3)   | Country                                           | yes          | country_code              | no   |
| REGIO  | CHAR(3)   | Region                                            | yes          | region_code               | no   |
| ORT01  | CHAR(35)  | City                                              | yes          | city                      | no   |
| FABKL  | CHAR(2)   | Factory calendar key (FK → TFACS)                 | yes          | factory_calendar_id       | no   |
| EKORG  | CHAR(4)   | Purchasing organization                           | yes          | purchasing_org_id         | no   |
| VKORG  | CHAR(4)   | Sales organization                                | yes          | sales_org_id              | no   |
| KUNNR  | CHAR(10)  | Customer number (intercompany stock transfer)     | yes          | intercompany_customer_id  | no   |
| LIFNR  | CHAR(10)  | Vendor number (intercompany)                      | yes          | intercompany_vendor_id    | no   |

---

## 3. Khối lượng & growth

> Số ước tính bên dưới là **synthetic baseline** cho portfolio (Bosch mid-size plant). Cần cập nhật nếu có số thực.

| Bảng | Rows hiện tại (ước) | Rows/day | Bronze size/year (CSV) | Strategy     |
| ---- | ------------------- | -------- | ---------------------- | ------------ |
| VBAK | ~500K               | ~500     | ~70MB                  | incremental (ERDAT) |
| VBAP | ~2M                 | ~2000    | ~400MB                 | incremental (ERDAT) |
| EKKO | ~200K               | ~200     | ~25MB                  | incremental (BEDAT) |
| EKPO | ~600K               | ~600     | ~80MB                  | incremental (BEDAT) |
| MSEG | ~5M                 | ~900     | ~600MB                 | incremental (BUDAT) |
| MARA | ~50K                | ~10      | ~5MB                   | full reload (daily) |
| MARC | ~150K               | ~20      | ~15MB                  | full reload (daily) |
| MARD | ~200K               | ~100     | ~25MB                  | full reload (hourly snapshot) |
| LFA1 | ~3K                 | ~2       | <1MB                   | full reload (daily) |
| KNA1 | ~5K                 | ~5       | <1MB                   | full reload (daily) |

**Rule of thumb áp dụng:**
- Master data (MARA, MARC, MARD, LFA1, KNA1) → full reload vì nhỏ, thay đổi không dự đoán được
- Transaction data (VBAK, VBAP, EKKO, EKPO, MSEG) → incremental theo ngày tạo (`ERDAT`/`BEDAT`/`BUDAT`)
- MSEG là bảng lớn nhất — nếu Bosch production > 5M rows thì **bắt buộc incremental**

---

## 4. Cách extract từ SAP

### 4.1 Manual (Phase 1 — học)

1. Log SAP GUI → `SE16` hoặc `SE16N`
2. Nhập tên bảng (vd `VBAK`)
3. Filter ngày (`ERDAT >= 2025-01-01`)
4. *List → Save → Local file → Spreadsheet (XLSX)* hoặc *Unconverted (TXT)*
5. Convert sang CSV (UTF-8, comma) bằng Excel hoặc script
6. Đặt vào `data/raw/se16/<table>/<table>_YYYYMMDD.csv`

### 4.2 Tự động (Phase 5+ — sau khi đã quen)

Có 3 hướng, chọn 1:

- **(A) Theo dõi qua SAP Open Hub Service** → đẩy ra file system / Azure Blob → ingest. (Cần quyền BW)
- **(B) RFC + `pyrfc`** Python library — kết nối trực tiếp SAP qua RFC. (Cần SAP credentials + library nặng)
- **(C) CDC từ database tier (Debezium → Kafka)** — chỉ làm được khi có quyền database (HANA/Oracle), thường không có. *Production-grade nhất nhưng khó nhất.*

> **Cho project portfolio:** đi (A) hoặc (B) là realistic. Bạn ghi rõ "approach C đã được cân nhắc nhưng không khả thi do quyền truy cập" — đây là cách trả lời chững chạc khi recruiter hỏi.

**Quyết định:**

```
Phase 1 (portfolio): Generate synthetic CSV bằng Python + Faker, đúng schema SAP ECC 6.0.
Lý do: không export production data Bosch vì compliance. Synthetic đủ để demo pipeline end-to-end
và chứng minh hiểu schema SAP.

Phase 5+ (nếu có quyền): cân nhắc approach (B) pyrfc hoặc (A) Open Hub Service.
Approach (C) CDC/Debezium bị loại ngay vì không có database-level access ở Bosch.
```

---

## 5. Compliance & PII

- [x] Đã review danh sách field PII: ERNAM (created_by), KUNNR/KNA1.NAME1 (customer), LFA1.NAME1 (vendor)
- [x] Approach: dùng synthetic data → PII không tồn tại. Nếu sau này dùng real data, hash SHA-256 trước Bronze.
- [x] Không commit data lên Git — `data/` đã có trong `.gitignore`
- [ ] Nếu muốn dùng real data (kể cả đã anonymize): phải hỏi IT-Compliance Bosch trước

> **Tuyệt đối không** copy data thật của Bosch lên repo public. Khi cần show ra ngoài, tốt nhất generate synthetic data **đúng schema** trên cùng cấu trúc đã thiết kế.

---

## 6. ERD

> Vẽ tay hoặc dùng dbdiagram.io / drawio. Lưu ảnh `docs/img/erd_sap_source.png`.
> Tối thiểu cần show: VBAK→VBAP→LIKP→LIPS, EKKO→EKPO→EKET, MARA-MARC-MARD.

---

## 7. Open questions

- [x] ~~SAP version?~~ → ECC 6.0 classic. Không có ACDOCA.
- [ ] Bosch có bảng **custom Z\*** không? (vd ZVBAK_EXT cho thêm field nội bộ) — nếu có, cần thêm vào Section 1
- [ ] Bosch dùng **fiscal year** đặc biệt không? (T009 — ảnh hưởng cách group by period trong dbt marts)
- [ ] Plant code (`WERKS`) của bạn là gì? (cần để filter synthetic data realistic)

Khi điền xong ERD (Section 6) và commit, ping: *"Step 1.1 xong, qua step kế."*
