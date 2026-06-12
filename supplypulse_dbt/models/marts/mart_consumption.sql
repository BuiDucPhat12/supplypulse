-- Daily demand per material. Null rows của int_backlog (requirement_date IS NULL,
-- chỉ giữ overdue signal) được exclude — backlog đã xử lý riêng ở simulation.
SELECT
    marc_id,
    MAX(material_number) AS material_number,
    MAX(plant)           AS plant,
    requirement_date,
    SUM(demand_qty)      AS daily_consumption
FROM {{ ref('int_backlog') }}
WHERE requirement_date IS NOT NULL
GROUP BY marc_id, requirement_date
