-- SA lines còn open quantity + planned_availability_date (PAD).
-- PAD = delivery_date + gr_processing_days WORKING days (Cách 2 pattern):
--   fc xử lý cuối tuần (technical_day_number + snap), wc tính offset.
-- Không filter theo ngày: delivery_date quá khứ + open_qty > 0 = overdue supply, vẫn giữ.
WITH sa AS (
    SELECT * FROM {{ ref('int_scheduling_agreement') }}
    WHERE open_quantity > 0
),

tt AS (
    SELECT ekpo_id, transit_time_days, quote_percent
    FROM {{ ref('int_purchasing_document_tt') }}
),

marc AS (
    SELECT marc_id, gr_processing_days
    FROM {{ ref('stg_marc') }}
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

joined AS (
    SELECT
        sa.ekpo_id,
        sa.po_number,
        sa.po_item,
        sa.vendor_number,
        lfa1.vendor_name,
        lfa1.country,
        sa.purchasing_org,
        sa.po_type,
        sa.po_date,
        sa.marc_id,
        sa.material_number,
        sa.plant,
        sa.delivery_date,
        sa.scheduled_quantity,
        sa.goods_receipt_quantity,
        sa.open_quantity,
        marc.gr_processing_days,
        tt.transit_time_days,
        tt.quote_percent,
        -- Fallback calendar days khi delivery_date ngoài range của fc
        COALESCE(
            wc.calendar_date,
            sa.delivery_date + COALESCE(marc.gr_processing_days, 0)::int
        ) AS planned_availability_date
    FROM sa
    LEFT JOIN marc ON sa.marc_id = marc.marc_id
    LEFT JOIN tt ON sa.ekpo_id = tt.ekpo_id
    LEFT JOIN lfa1 ON sa.vendor_number = lfa1.vendor_number
    LEFT JOIN fc
        ON  sa.plant = fc.plant
        AND sa.delivery_date = fc.calendar_date
    LEFT JOIN wc
        ON  sa.plant = wc.plant
        AND wc.working_day_index = fc.technical_day_number
            + (CASE WHEN fc.is_workingday = 0 THEN 1 ELSE 0 END)
            + COALESCE(marc.gr_processing_days, 0)::int
)

SELECT * FROM joined
