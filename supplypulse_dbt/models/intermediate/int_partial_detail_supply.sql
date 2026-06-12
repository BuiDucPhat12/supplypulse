-- Supply events + context material (stock, planning params) + calendar.
-- Filter planned_availability_date IS NOT NULL (ASN 'pending' bị loại ở đây).
WITH s AS (
    SELECT * FROM {{ ref('int_supply') }}
    WHERE planned_availability_date IS NOT NULL
),

pn AS (
    SELECT * FROM {{ ref('int_pn_infor') }}
),

q AS (
    SELECT * FROM {{ ref('int_tt_quota') }}
),

fc AS (
    SELECT * FROM {{ ref('int_factory_calendar') }}
)

SELECT
    s.supply_type,
    s.marc_id,
    s.material_number,
    s.plant,
    s.vendor_number,
    s.vendor_name,
    s.country,
    s.planned_availability_date,
    s.order_qty,
    s.order_qty_due,
    s.fulfill_qty,
    pn.available_stock,
    pn.safety_stock,
    pn.abc_indicator,
    pn.gr_processing_days,
    q.transit_time_days,
    q.quote_percent,
    q.max_tt,
    fc.is_workingday,
    fc.technical_day_number
FROM s
LEFT JOIN pn ON s.marc_id = pn.marc_id
LEFT JOIN q
    ON  s.marc_id = q.marc_id
    AND s.vendor_number = q.vendor_number
LEFT JOIN fc
    ON  s.plant = fc.plant
    AND s.planned_availability_date = fc.calendar_date
