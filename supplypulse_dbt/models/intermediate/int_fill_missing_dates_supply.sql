-- mart_detail_supply cần daily continuity cho running SUM OVER (ORDER BY date):
-- thiếu ngày → sum nhảy cóc → sai. Model này bù mọi ngày thiếu trong 120-day window
-- với qty = 0 cho từng cặp (marc_id, vendor) đang có 'Order Qty' supply.
-- Cột context (stock, TT...) để NULL — fill rows chỉ phục vụ continuity.
WITH pds AS (
    SELECT * FROM {{ ref('int_partial_detail_supply') }}
),

pairs AS (
    SELECT DISTINCT
        marc_id,
        material_number,
        plant,
        vendor_number,
        vendor_name,
        country
    FROM pds
    WHERE supply_type = 'Order Qty'
),

fc AS (
    SELECT * FROM {{ ref('int_factory_calendar') }}
    WHERE calendar_date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '120 days'
),

grid AS (
    SELECT
        pairs.marc_id,
        pairs.material_number,
        pairs.plant,
        pairs.vendor_number,
        pairs.vendor_name,
        pairs.country,
        fc.calendar_date,
        fc.is_workingday,
        fc.technical_day_number
    FROM pairs
    INNER JOIN fc ON pairs.plant = fc.plant
)

SELECT
    'Order Qty'            AS supply_type,
    g.marc_id,
    g.material_number,
    g.plant,
    g.vendor_number,
    g.vendor_name,
    g.country,
    g.calendar_date        AS planned_availability_date,
    0::numeric             AS order_qty,
    0::numeric             AS order_qty_due,
    NULL::numeric          AS fulfill_qty,
    NULL::numeric          AS available_stock,
    NULL::numeric          AS safety_stock,
    NULL::text             AS abc_indicator,
    NULL::numeric          AS gr_processing_days,
    NULL::int              AS transit_time_days,
    NULL::numeric          AS quote_percent,
    NULL::int              AS max_tt,
    g.is_workingday,
    g.technical_day_number
FROM grid g
WHERE NOT EXISTS (
    SELECT 1
    FROM pds
    WHERE pds.marc_id = g.marc_id
      AND pds.vendor_number = g.vendor_number
      AND pds.planned_availability_date = g.calendar_date
)
