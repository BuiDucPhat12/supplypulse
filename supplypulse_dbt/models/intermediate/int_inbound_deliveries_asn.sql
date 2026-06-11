-- ASN = inbound deliveries chưa GR hoàn tất (goods_movement_status != 'C').
-- Vendor không có trong LIKP — trace qua lips.reference_document = ekko.po_number.
-- PAD = gr_date + gr_processing_days working days (Cách 2). KHÔNG fallback calendar days:
-- PAD NULL (gr_date ngoài range fc) = asn_status 'pending', xử lý riêng.
WITH ind AS (
    SELECT * FROM {{ ref('int_inbound_deliveries') }}
    WHERE COALESCE(goods_movement_status, '') != 'C'
),

ekko AS (
    SELECT po_number, vendor_number
    FROM {{ ref('stg_ekko') }}
),

lfa1 AS (
    SELECT vendor_number, vendor_name, country
    FROM {{ ref('stg_lfa1') }}
),

fc AS (
    SELECT * FROM {{ ref('int_factory_calendar') }}
),

wc AS (
    SELECT * FROM {{ ref('int_working_calendar') }}
),

with_pad AS (
    SELECT
        ind.delivery_number,
        ind.delivery_item,
        ind.delivery_type,
        ind.marc_id,
        ind.material_number,
        ind.plant,
        ekko.vendor_number,
        lfa1.vendor_name,
        lfa1.country,
        ind.created_date,
        ind.planned_delivery_date_hdr,
        ind.gr_date,
        ind.gr_processing_days,
        ind.delivery_quantity,
        ind.goods_movement_status,
        wc.calendar_date AS planned_availability_date
    FROM ind
    LEFT JOIN ekko ON ind.reference_document = ekko.po_number
    LEFT JOIN lfa1 ON ekko.vendor_number = lfa1.vendor_number
    LEFT JOIN fc
        ON  ind.plant = fc.plant
        AND ind.gr_date = fc.calendar_date
    LEFT JOIN wc
        ON  ind.plant = wc.plant
        AND wc.working_day_index = fc.technical_day_number
            + (CASE WHEN fc.is_workingday = 0 THEN 1 ELSE 0 END)
            + COALESCE(ind.gr_processing_days, 0)::int
),

with_status AS (
    SELECT
        *,
        CASE
            WHEN planned_availability_date IS NULL THEN 'pending'
            WHEN planned_availability_date >= CURRENT_DATE THEN 'future'
            ELSE 'overdue'
        END AS asn_status
    FROM with_pad
)

SELECT
    *,
    -- Tổng ASN đã quá hạn/treo per material (toàn material, không phân biệt vendor)
    -- — mart_inventory_simulation dùng để biết lượng hàng "đáng ra đã đến"
    SUM(CASE WHEN asn_status IN ('overdue', 'pending') THEN delivery_quantity ELSE 0 END)
        OVER (PARTITION BY marc_id) AS asn_total_due_qty
FROM with_status
