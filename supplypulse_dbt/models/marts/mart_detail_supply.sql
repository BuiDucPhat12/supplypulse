-- Supply chi tiết daily-continuous: events thật + fill rows 0-qty.
-- Fill rows có NULL ở các cột context — không ảnh hưởng mart_inventory_simulation
-- (simulation source trực tiếp từ int_pn_infor).
SELECT * FROM {{ ref('int_partial_detail_supply') }}

UNION ALL

SELECT * FROM {{ ref('int_fill_missing_dates_supply') }}
