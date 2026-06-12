-- Vendor scorecard cho dashboard Page 3.
-- OTD đo trên deliveries đã GR hoàn tất (goods_movement_status = 'C'):
--   on-time = gr_date <= planned_delivery_date_hdr (LIKP.LFDAT = ngày hẹn theo SA).
-- Late shipment lines lấy từ int_sa_late_shipment (flag = 1).
WITH ind AS (
    SELECT * FROM {{ ref('int_inbound_deliveries') }}
),

ekko AS (
    SELECT po_number, vendor_number
    FROM {{ ref('stg_ekko') }}
),

deliveries AS (
    SELECT
        ekko.vendor_number,
        ind.gr_date,
        ind.planned_delivery_date_hdr,
        ind.delivery_quantity,
        ind.goods_movement_status
    FROM ind
    INNER JOIN ekko ON ind.reference_document = ekko.po_number
),

otd AS (
    SELECT
        vendor_number,
        COUNT(*) AS completed_delivery_lines,
        COUNT(*) FILTER (WHERE gr_date <= planned_delivery_date_hdr) AS on_time_lines
    FROM deliveries
    WHERE goods_movement_status = 'C'
    GROUP BY vendor_number
),

late AS (
    SELECT
        vendor_number,
        COUNT(*) FILTER (WHERE late_shipment_flag = 1)            AS late_shipment_lines,
        COALESCE(SUM(order_qty_due) FILTER (WHERE late_shipment_flag = 1), 0) AS late_qty_due
    FROM {{ ref('int_sa_late_shipment') }}
    GROUP BY vendor_number
),

tt AS (
    SELECT
        vendor_number,
        AVG(transit_time_days) AS avg_transit_time_days
    FROM {{ ref('int_transit_time') }}
    GROUP BY vendor_number
),

lfa1 AS (
    SELECT vendor_number, vendor_name, country
    FROM {{ ref('stg_lfa1') }}
)

SELECT
    lfa1.vendor_number,
    lfa1.vendor_name,
    lfa1.country,
    COALESCE(otd.completed_delivery_lines, 0) AS completed_delivery_lines,
    COALESCE(otd.on_time_lines, 0)            AS on_time_lines,
    ROUND(
        otd.on_time_lines::numeric / NULLIF(otd.completed_delivery_lines, 0),
        3
    )                                         AS otd_rate,
    COALESCE(late.late_shipment_lines, 0)     AS late_shipment_lines,
    COALESCE(late.late_qty_due, 0)            AS late_qty_due,
    ROUND(tt.avg_transit_time_days, 1)        AS avg_transit_time_days
FROM lfa1
LEFT JOIN otd  ON lfa1.vendor_number = otd.vendor_number
LEFT JOIN late ON lfa1.vendor_number = late.vendor_number
LEFT JOIN tt   ON lfa1.vendor_number = tt.vendor_number
