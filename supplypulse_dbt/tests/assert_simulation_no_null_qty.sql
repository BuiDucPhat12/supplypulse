-- simulated_inventory_qty NULL = có marc_id lọt grid mà thiếu available_stock
-- (chính là bug NULL stock đã fix bằng gen_ekpo marc_combos)
SELECT marc_id, calendar_date
FROM {{ ref('mart_inventory_simulation') }}
WHERE simulated_inventory_qty IS NULL
