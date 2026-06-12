-- Mô phỏng tồn kho 120 ngày per material:
--   simulated_inventory_qty =
--       available_stock                 (hằng số — tồn hiện tại)
--     - backlog_qty                     (hằng số — overdue demand tích lũy TRƯỚC anchor,
--                                        là debt có sẵn nên trừ ngay từ ngày đầu, không SUM OVER)
--     - SUM(daily_consumption) lũy kế   (demand phát sinh TỪNG NGÀY → tích lũy)
--     + SUM(daily_asn_qty) lũy kế       (supply về TỪNG NGÀY → tích lũy)
-- simulated_inventory_qty < 0 = red day.
WITH pn AS (
    SELECT * FROM {{ ref('int_pn_infor') }}
),

fc AS (
    SELECT * FROM {{ ref('int_factory_calendar') }}
    WHERE calendar_date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '120 days'
),

grid AS (
    SELECT
        pn.marc_id,
        pn.material_number,
        pn.plant,
        pn.abc_indicator,
        pn.available_stock,
        pn.safety_stock,
        fc.calendar_date
    FROM pn
    INNER JOIN fc ON pn.plant = fc.plant
),

consumption AS (
    SELECT
        marc_id,
        requirement_date,
        SUM(demand_qty) AS daily_consumption
    FROM {{ ref('int_backlog') }}
    WHERE requirement_date IS NOT NULL
    GROUP BY marc_id, requirement_date
),

backlog AS (
    SELECT
        marc_id,
        MAX(backlog_per_pn) AS backlog_qty
    FROM {{ ref('int_backlog') }}
    GROUP BY marc_id
),

asn AS (
    SELECT
        marc_id,
        planned_availability_date,
        SUM(delivery_quantity) AS daily_asn_qty
    FROM {{ ref('int_inbound_deliveries_asn') }}
    WHERE asn_status = 'future'
    GROUP BY marc_id, planned_availability_date
),

daily AS (
    SELECT
        g.marc_id,
        g.material_number,
        g.plant,
        g.abc_indicator,
        g.available_stock,
        g.safety_stock,
        g.calendar_date,
        COALESCE(b.backlog_qty, 0)        AS backlog_qty,
        COALESCE(c.daily_consumption, 0)  AS daily_consumption,
        COALESCE(a.daily_asn_qty, 0)      AS daily_asn_qty
    FROM grid g
    LEFT JOIN backlog b ON g.marc_id = b.marc_id
    LEFT JOIN consumption c
        ON  g.marc_id = c.marc_id
        AND g.calendar_date = c.requirement_date
    LEFT JOIN asn a
        ON  g.marc_id = a.marc_id
        AND g.calendar_date = a.planned_availability_date
)

SELECT
    *,
    available_stock
        - backlog_qty
        - SUM(daily_consumption) OVER (PARTITION BY marc_id ORDER BY calendar_date)
        + SUM(daily_asn_qty)     OVER (PARTITION BY marc_id ORDER BY calendar_date)
    AS simulated_inventory_qty
FROM daily
