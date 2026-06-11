SELECT marc_id, red_days
FROM {{ ref('mart_shortage_report') }}
WHERE red_days < 0
