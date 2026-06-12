# ERD — Production DALI Transform Pipeline

```mermaid
erDiagram

%% ══════════════════════════════════════════════
%% RAW TABLES (dali_raw_data)
%% ══════════════════════════════════════════════

    marc {
        text marc_bbm_id PK
        varchar logsys
        varchar matnr
        varchar werks
        numeric webaz
        varchar dispo
        varchar beskz
        varchar fxhor
        numeric eisbe
        varchar shzet
        varchar shflg
    }

    mard {
        varchar logsys
        varchar matnr
        varchar werks
        varchar lgort
        varchar diskz
        numeric labst
        numeric klabs
        numeric speme
        numeric insme
    }

    ekko {
        varchar logsys
        varchar ebeln PK
        varchar lifnr
        varchar ekorg
    }

    ekpo {
        varchar logsys
        varchar ebeln FK
        varchar ebelp PK
        varchar matnr
        varchar werks
        varchar loekz
        varchar bstyp
        varchar evers
    }

    eket {
        text ekpo_bbm_id FK
        text ekko_bbm_id FK
        varchar logsys
        varchar ebeln
        varchar ebelp
        varchar eindt
        numeric menge
        numeric wemng
        numeric omenge
    }

    equk {
        varchar logsys
        varchar matnr
        varchar werks
        varchar qunum PK
        varchar bdatu
        varchar vdatu
        varchar erdat
    }

    equp {
        varchar logsys
        varchar qunum FK
        varchar qupos PK
        varchar lifnr
        numeric quote
        varchar relation
    }

    vbbe {
        varchar logsys
        varchar matnr
        varchar werks
        varchar bdart
        varchar bdter
        numeric bdmng
        varchar baugr
        varchar mbdat
        numeric omeng
    }

    resb {
        varchar logsys
        varchar matnr
        varchar werks
        varchar bdart
        varchar bdter
        numeric bdmng
        varchar baugr
    }

    likp {
        varchar logsys
        varchar vbeln PK
        varchar lifnr
        varchar lifex
        varchar lfdat
        varchar wadat_ist
        varchar erdat
    }

    vbup_lips {
        varchar logsys
        varchar vbeln FK
        varchar posnr PK
        varchar matnr
        varchar werks
        varchar vgbel
        numeric lfimg
    }

    vbup {
        varchar logsys
        varchar vbeln FK
        varchar posnr PK
        varchar wbsta
    }

    rb04 {
        varchar logsys
        varchar ekorg
        varchar werks
        varchar lifnr
        varchar evers
        varchar rb04_yl1_transt
        varchar fabkl
    }

    lfa1 {
        text lfa1_bbm_id PK
        varchar logsys
        varchar lifnr
        varchar name1
    }

    t001w {
        varchar logsys
        varchar werks PK
        varchar fabkl
        varchar lifnr
    }

    fac_calender {
        varchar logsys
        varchar calendar_dt
        varchar ident
        varchar is_workingday
    }

    bom_parent_child {
        varchar logsys
        varchar parent_matnr
        varchar child_matnr
    }

%% ══════════════════════════════════════════════
%% LAYER 1 — MATERIAL MASTER
%% ══════════════════════════════════════════════

    material_bbm {
        text marc_bbm_id PK
        numeric webaz
        varchar matnr
    }

    PN_Infor {
        varchar material_id PK
        text marc_bbm_id
        varchar pn
        varchar logsys
        varchar werks
        text plant_sys
        varchar mrpc
        varchar proc_type
        numeric processing_time
        varchar safety_time
        integer safety_time_indicator
        numeric safety_stock
        numeric blocked_stock_q
        numeric blocked_stock_s
        numeric available_stock
        varchar fc
    }

%% ══════════════════════════════════════════════
%% LAYER 2 — CALENDAR
%% ══════════════════════════════════════════════

    working_calendar {
        varchar logsys
        varchar ident
        date calendar_dt PK
        integer working_day_index
    }

    factory_calendar_inventory_simulation {
        varchar logsys
        varchar ident
        date calendar_dt PK
        integer is_workingday
        integer technical_day_number
        date jump_to_wd_date
        date prev_wd
        date next_wd
        integer prev_day_is_not_wd
        integer next_day_is_not_wd
    }

%% ══════════════════════════════════════════════
%% LAYER 3 — QUOTA & TRANSIT TIME
%% ══════════════════════════════════════════════

    equk_bbm_active {
        text equk_bbm_id PK
        text marc_bbm_id FK
        text mara_bbm_id
        text t001w_bbm_id
        text qunum_j
        varchar logsys
        varchar qunum
        varchar matnr
        varchar werks
        varchar bdatu
        date vdatu_n
        date bdatu_n
        boolean is_valid
    }

    equp_bbm_active {
        text equp_bbm_id PK
        text lfa1_bbm_id
        text qunum_j FK
        varchar logsys
        varchar qunum
        integer quote
        varchar qupos
        varchar lifnr
        varchar relation
    }

    valid_quote_agreements {
        text equp_bbm_id FK
        text marc_bbm_id PK
        text lfa1_bbm_id FK
        varchar logsys
        varchar matnr
        varchar werks
        varchar lifnr
        varchar qunum
        integer quote
        bigint total_quote
        text material_source_id
        float quote_percent
    }

    rb04_yl1_ediwkn_bbm_active {
        text rb04_yl1_ediwkn_bbm_id PK
        text lfa1_bbm_id FK
        text t001w_bbm_id FK
        text transport_time_join_id
        varchar logsys
        varchar ekorg
        varchar werks
        varchar lifnr
        varchar evers
        integer rb04_yl1_transt
        varchar fabkl
    }

%% ══════════════════════════════════════════════
%% LAYER 4 — PURCHASING DOCUMENTS
%% ══════════════════════════════════════════════

    purchasing_document_active {
        text ekpo_bbm_id PK
        text marc_bbm_id FK
        text rb04_yl1_ediwkn_bbm_id FK
        text transport_time_join_id
        varchar logsys
        varchar ebeln
        varchar ebelp
        varchar werks
        varchar matnr
        varchar lifnr
        varchar ekorg
        varchar evers
        varchar bstyp
    }

    purchasing_document_transit_time {
        text ekpo_bbm_id FK
        text marc_bbm_id FK
        numeric rb04_yl1_transt
        varchar fabkl
        varchar evers_ediwkn
        float quote_percent
    }

%% ══════════════════════════════════════════════
%% LAYER 5 — DEMAND (BACKLOG)
%% ══════════════════════════════════════════════

    backlog {
        text marc_bbm_id FK
        text backlog_of_planned_orders_id PK
        varchar matnr
        varchar werks
        varchar logsys
        varchar bdart
        date bdter
        numeric bdmng
        numeric backlog_per_pn_contype
        numeric backlog_per_pn
        varchar baugr
    }

%% ══════════════════════════════════════════════
%% LAYER 6 — SUPPLY SCHEDULE
%% ══════════════════════════════════════════════

    scheduling_agreement_by_delivery_date {
        text ekpo_bbm_id PK
        varchar logsys
        varchar ebeln
        varchar ebelp
        varchar eindt PK
        numeric menge
        numeric wemng
        numeric omenge
    }

    scheduling_agreement {
        text ekpo_bbm_id PK
        text marc_bbm_id FK
        text transport_time_join_id
        varchar logsys
        varchar ebeln
        varchar ebelp
        varchar eindt
        varchar werks
        varchar matnr
        varchar lifnr
        numeric omenge
        varchar bstyp
        varchar evers
    }

    total_due_scheduling_agreement_groupped {
        text scheduling_agreement_future_id PK
        varchar matnr
        varchar werks
        varchar ebeln
        varchar logsys
        varchar lifnr
        numeric total_due_quantity
    }

    scheduling_agreement_future {
        text saf_id PK
        text marc_bbm_id FK
        text lfa1_bbm_id FK
        varchar logsys
        varchar matnr
        varchar werks
        varchar ebeln
        varchar ebelp
        varchar lifnr
        varchar name1
        numeric processing_time
        varchar eindt
        numeric open_quantity
        numeric rb04_yl1_transt
        float quote_percent
        timestamp planned_availability_date
        numeric total_due_quantity
    }

    scheduling_agreement_late_shipment {
        text saf_id FK
        text marc_bbm_id FK
        varchar logsys
        varchar matnr
        varchar werks
        varchar lifnr
        timestamp planned_availability_date
        timestamp end_tt
        numeric order_qty
        numeric order_qty_due
        numeric asn
        numeric asn_due
        integer tt
        numeric fulfill_qty
        integer late_shipment_flag
    }

%% ══════════════════════════════════════════════
%% LAYER 7 — INBOUND DELIVERIES (ASN)
%% ══════════════════════════════════════════════

    inbound_deliveries {
        text marc_bbm_id FK
        text t001w_bbm_id
        text lfa1_bbm_id FK
        varchar logsys
        varchar vbeln FK
        varchar werks
        varchar matnr
        varchar posnr
        varchar vgbel
        numeric lfimg
        varchar erdat
        varchar lfdat
        varchar wadat_ist
        varchar lifnr
        varchar budat_mkpf
    }

    inbound_deliveries_asn {
        text deliveries_asn_id PK
        text marc_bbm_id FK
        text material_id
        text plant_id
        text vendor_id
        varchar matnr
        varchar werks
        varchar logsys
        varchar vendor
        varchar vendor_name
        varchar mmsa
        varchar vbeln
        varchar fxhor
        varchar beskz
        date gr_date_planned
        integer processing_time
        date gr_date_actual
        date planned_availability_date
        numeric asn_quantity
        numeric asn_total_due_qty
        text transit_time
        float quote_percent
    }

%% ══════════════════════════════════════════════
%% LAYER 8 — SUPPLY CONSOLIDATION
%% ══════════════════════════════════════════════

    supply {
        text marc_bbm_id FK
        varchar matnr
        text system_plant
        varchar vendor_code
        varchar vendor_name
        text type_of_supply
        numeric due_qty
        integer late_shipment_flag
        timestamp planned_availability_date
        numeric qty
        numeric fulfill_qty
        float quota
        varchar mmsa
        integer tt
    }

    TT_Quota {
        varchar material_id FK
        text plant_sys
        varchar pn
        varchar plant
        varchar mmsa
        varchar vendor
        varchar shipping_mode
        numeric tt
        float quota
        varchar vendor_name
        numeric max_tt
    }

    partial_detail_supply {
        text marc_bbm_id FK
        varchar pn
        text plant_sys
        varchar vendor_code
        varchar vendor_name
        varchar mmsa
        text type_of_supply
        numeric due_qty
        timestamp planned_availability_date
        numeric qty
        numeric fulfill_qty
        numeric tt
        numeric processing_time
        integer fz
        integer is_workingday
    }

    fill_missing_dates_supply {
        text marc_bbm_id FK
        varchar vendor_code
        varchar mmsa
        text type_of_supply
        date planned_availability_date
        integer qty
        integer fulfill_qty
        integer due_qty
        integer is_workingday
    }

    final_detail_supply {
        text marc_bbm_id FK
        varchar pn
        text plant_sys
        varchar vendor_code
        varchar mmsa
        text type_of_supply
        numeric due_qty
        timestamp planned_availability_date
        numeric qty
        numeric fulfill_qty
        numeric tt
        numeric processing_time
    }

%% ══════════════════════════════════════════════
%% LAYER 9 — INVENTORY SIMULATION
%% ══════════════════════════════════════════════

    inventory_simulation {
        text inventory_simulation_id PK
        varchar marc_bbm_id FK
        varchar logsys
        varchar matnr
        varchar werks
        numeric available_stock
        date planned_availability_date
        integer is_workingday
        numeric lfimg
        numeric consumption
        numeric backlog
        numeric simulated_inventory_qty
        numeric transit_time
    }

%% ══════════════════════════════════════════════
%% LAYER 10 — CONSUMPTION & BOM
%% ══════════════════════════════════════════════

    Consumption {
        text cs_id PK
        text material_id FK
        varchar pn
        varchar bdart
        date consumption_date
        numeric consumption_quantity
        numeric backlog_quantity
        varchar pn_next_level
    }

    bom_FG_filtered {
        varchar logsys
        varchar parent_matnr PK
        varchar child_matnr PK
    }

    filtered_vbbe_resb {
        text material_id FK
        date consumption_date PK
        numeric resb_consumption_qty
        numeric vbbe_consumption_qty
    }

%% ══════════════════════════════════════════════
%% RELATIONSHIPS — RAW → LAYER 1
%% ══════════════════════════════════════════════

    marc ||--o{ material_bbm : "marc_bbm_id"
    marc ||--|| PN_Infor : "logsys+matnr+werks"
    mard }o--|| PN_Infor : "logsys+matnr+werks"

%% RAW → LAYER 2

    fac_calender ||--o{ working_calendar : "logsys+ident+calendar_dt"
    fac_calender ||--o{ factory_calendar_inventory_simulation : "logsys+ident+calendar_dt"

%% RAW → LAYER 3

    equk ||--|| equk_bbm_active : "logsys+matnr+werks+bdatu"
    equp ||--|| equp_bbm_active : "logsys+qunum+qupos"
    equk_bbm_active ||--o{ valid_quote_agreements : "qunum_j"
    equp_bbm_active ||--o{ valid_quote_agreements : "qunum_j"
    rb04 ||--|| rb04_yl1_ediwkn_bbm_active : "logsys+ekorg+werks+lifnr+evers"
    lfa1 ||--o{ valid_quote_agreements : "lfa1_bbm_id"

%% RAW → LAYER 4

    ekko ||--o{ purchasing_document_active : "logsys+ebeln"
    ekpo ||--o{ purchasing_document_active : "logsys+ebeln+ebelp"
    marc ||--o{ purchasing_document_active : "logsys+matnr+werks"
    purchasing_document_active ||--|| purchasing_document_transit_time : "ekpo_bbm_id"
    rb04_yl1_ediwkn_bbm_active ||--o{ purchasing_document_transit_time : "rb04_yl1_ediwkn_bbm_id"
    valid_quote_agreements ||--o{ purchasing_document_transit_time : "marc_bbm_id+lifnr"

%% RAW → LAYER 5

    resb ||--o{ backlog : "logsys+matnr+werks+bdart"
    vbbe ||--o{ backlog : "logsys+matnr+werks+bdart"
    resb ||--o{ filtered_vbbe_resb : "logsys+matnr+werks+bdter"
    vbbe ||--o{ filtered_vbbe_resb : "logsys+matnr+werks+mbdat"

%% RAW → LAYER 6

    eket ||--o{ scheduling_agreement_by_delivery_date : "ekpo_bbm_id+eindt"
    purchasing_document_active ||--|| scheduling_agreement : "ekpo_bbm_id"
    scheduling_agreement_by_delivery_date ||--o{ scheduling_agreement : "ekpo_bbm_id"
    scheduling_agreement ||--o{ scheduling_agreement_future : "marc_bbm_id+ebeln"
    total_due_scheduling_agreement_groupped ||--o{ scheduling_agreement_future : "saf_id"
    lfa1 ||--o{ scheduling_agreement_future : "lfa1_bbm_id"
    valid_quote_agreements ||--o{ scheduling_agreement_future : "lfa1_bbm_id+marc_bbm_id"
    factory_calendar_inventory_simulation ||--o{ scheduling_agreement_future : "logsys+ident"
    working_calendar ||--o{ scheduling_agreement_future : "logsys+ident"
    scheduling_agreement_future ||--o{ scheduling_agreement_late_shipment : "saf_id+marc_bbm_id"

%% RAW → LAYER 7

    likp ||--o{ inbound_deliveries : "logsys+vbeln"
    vbup_lips ||--o{ inbound_deliveries : "logsys+vbeln+posnr"
    marc ||--o{ inbound_deliveries : "logsys+matnr+werks"
    inbound_deliveries ||--o{ inbound_deliveries_asn : "lips_bbm_id"
    vbup ||--o{ inbound_deliveries_asn : "vbup_bbm_id"
    factory_calendar_inventory_simulation ||--o{ inbound_deliveries_asn : "logsys+ident+calendar_dt"
    working_calendar ||--o{ inbound_deliveries_asn : "logsys+ident"
    purchasing_document_active ||--o{ inbound_deliveries_asn : "logsys+werks+ebeln"
    rb04 ||--o{ inbound_deliveries_asn : "logsys+werks+lifnr+evers"
    lfa1 ||--o{ inbound_deliveries_asn : "lfa1_bbm_id"
    valid_quote_agreements ||--o{ inbound_deliveries_asn : "lfa1_bbm_id+marc_bbm_id"

%% LAYER 6+7 → LAYER 8

    scheduling_agreement_late_shipment ||--o{ supply : "marc_bbm_id (Order Qty)"
    inbound_deliveries_asn ||--o{ supply : "marc_bbm_id (ASN)"
    marc ||--o{ TT_Quota : "marc_bbm_id"
    purchasing_document_active ||--o{ TT_Quota : "logsys+werks+matnr"
    rb04 ||--o{ TT_Quota : "logsys+werks+lifnr+evers"
    lfa1 ||--o{ TT_Quota : "logsys+lifnr"
    valid_quote_agreements ||--o{ TT_Quota : "logsys+matnr+werks+lifnr"
    PN_Infor ||--o{ partial_detail_supply : "material_id"
    TT_Quota ||--o{ partial_detail_supply : "material_id+mmsa+vendor"
    supply ||--o{ partial_detail_supply : "marc_bbm_id+mmsa+vendor_code"
    factory_calendar_inventory_simulation ||--o{ partial_detail_supply : "logsys+ident+calendar_dt"
    partial_detail_supply ||--o{ fill_missing_dates_supply : "marc_bbm_id+vendor+mmsa"
    factory_calendar_inventory_simulation ||--o{ fill_missing_dates_supply : "logsys+ident"
    partial_detail_supply ||--o{ final_detail_supply : "marc_bbm_id"
    fill_missing_dates_supply ||--o{ final_detail_supply : "marc_bbm_id"

%% LAYERS → INVENTORY SIMULATION

    PN_Infor ||--o{ inventory_simulation : "marc_bbm_id (available_stock)"
    backlog ||--o{ inventory_simulation : "marc_bbm_id (consumption)"
    inbound_deliveries_asn ||--o{ inventory_simulation : "marc_bbm_id (lfimg/ASN)"
    factory_calendar_inventory_simulation ||--o{ inventory_simulation : "logsys+ident+calendar_dt"
    purchasing_document_transit_time ||--o{ inventory_simulation : "marc_bbm_id (transit_time)"
    t001w ||--o{ inventory_simulation : "logsys+werks→fabkl"

%% CONSUMPTION

    marc ||--o{ Consumption : "logsys+matnr+werks"
    backlog ||--o{ Consumption : "logsys+matnr+werks"

%% BOM

    bom_parent_child ||--o{ bom_FG_filtered : "parent_matnr+child_matnr"
```

---

## Chú thích

### Màu theo layer (nếu render hỗ trợ)

| Layer | Bảng |
|-------|------|
| **RAW** | `marc`, `mard`, `ekko`, `ekpo`, `eket`, `equk`, `equp`, `vbbe`, `resb`, `likp`, `vbup_lips`, `vbup`, `rb04`, `lfa1`, `t001w`, `fac_calender`, `bom_parent_child` |
| **L1 Material** | `material_bbm`, `PN_Infor` |
| **L2 Calendar** | `working_calendar`, `factory_calendar_inventory_simulation` |
| **L3 Quota/TT** | `equk_bbm_active`, `equp_bbm_active`, `valid_quote_agreements`, `rb04_yl1_ediwkn_bbm_active` |
| **L4 PO** | `purchasing_document_active`, `purchasing_document_transit_time` |
| **L5 Demand** | `backlog`, `filtered_vbbe_resb` |
| **L6 SA** | `scheduling_agreement_by_delivery_date`, `scheduling_agreement`, `total_due_scheduling_agreement_groupped`, `scheduling_agreement_future`, `scheduling_agreement_late_shipment` |
| **L7 ASN** | `inbound_deliveries`, `inbound_deliveries_asn` |
| **L8 Supply** | `supply`, `TT_Quota`, `partial_detail_supply`, `fill_missing_dates_supply`, `final_detail_supply` |
| **L9 Sim** | `inventory_simulation` |
| **L10 End** | `Consumption`, `bom_FG_filtered`, `filtered_vbbe_resb` |

### Key chung nhất

| Key | Các bảng dùng |
|-----|--------------|
| `marc_bbm_id` = `logsys-matnr-werks` | Hầu hết mọi bảng |
| `ekpo_bbm_id` = `logsys-ebeln-ebelp` | `purchasing_document_active`, `scheduling_agreement_*`, `eket` |
| `lfa1_bbm_id` = `logsys-lifnr` | `valid_quote_agreements`, `inbound_deliveries_asn`, `scheduling_agreement_future` |
| `qunum_j` = `logsys-qunum` | `equk_bbm_active`, `equp_bbm_active`, `valid_quote_agreements` |
| `saf_id` = `matnr-werks-logsys-ebeln-lifnr` | `scheduling_agreement_future`, `scheduling_agreement_late_shipment` |
| `transport_time_join_id` = `logsys-werks-lifnr-evers` | `purchasing_document_active` → `rb04` |
