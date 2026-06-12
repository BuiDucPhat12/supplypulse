-- Summary per material. status = 'Shortage' CHỈ khi có red day trong [today, end_of_tt_gr]:
-- trong TT window hàng đang trên đường, không can thiệp kịp → shortage không tránh được.
-- Red day SAU end_of_tt_gr: còn kịp đặt hàng mới → planning issue, không phải shortage.
WITH sim AS (
    SELECT * FROM {{ ref('mart_inventory_simulation') }}
),

tt AS (
    SELECT
        marc_id,
        MAX(max_tt) AS max_tt
    FROM {{ ref('int_tt_quota') }}
    GROUP BY marc_id
),

agg AS (
    SELECT
        sim.marc_id,
        MAX(sim.material_number)             AS material_number,
        MAX(sim.plant)                       AS plant,
        MAX(sim.abc_indicator)               AS abc_class,
        MAX(sim.available_stock)             AS available_stock,
        MAX(sim.safety_stock)                AS safety_stock,
        MAX(sim.backlog_qty)                 AS overdue_backlog_qty,
        MAX(COALESCE(tt.max_tt, 0))          AS max_tt,
        CURRENT_DATE + MAX(COALESCE(tt.max_tt, 0))::int AS end_of_tt_gr,
        COUNT(*) FILTER (WHERE sim.simulated_inventory_qty < 0) AS red_days,
        MIN(sim.simulated_inventory_qty) FILTER (
            WHERE sim.calendar_date <= CURRENT_DATE + COALESCE(tt.max_tt, 0)::int
        ) AS min_qty_in_tt_gr,
        COUNT(*) FILTER (
            WHERE sim.simulated_inventory_qty < 0
              AND sim.calendar_date <= CURRENT_DATE + COALESCE(tt.max_tt, 0)::int
        ) AS red_days_in_tt
    FROM sim
    LEFT JOIN tt ON sim.marc_id = tt.marc_id
    GROUP BY sim.marc_id
)

SELECT
    marc_id,
    material_number,
    plant,
    abc_class,
    available_stock,
    safety_stock,
    overdue_backlog_qty,
    max_tt,
    end_of_tt_gr,
    red_days,
    red_days_in_tt,
    min_qty_in_tt_gr,
    CASE WHEN red_days_in_tt > 0 THEN 'Shortage' ELSE 'No Shortage' END AS status
FROM agg
