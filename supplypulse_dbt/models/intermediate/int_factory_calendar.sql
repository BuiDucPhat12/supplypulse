WITH date_series AS (
    SELECT generate_series(
        DATE '2024-09-01',
        DATE '2024-09-01' + INTERVAL '180 days',
        INTERVAL '1 day'
    )::date AS calendar_date
),

plants AS (
    SELECT plant, factory_calendar_key
    FROM {{ ref('stg_t001w') }}
)

SELECT
    p.plant,
    p.factory_calendar_key,
    d.calendar_date,
    CASE WHEN EXTRACT(DOW FROM d.calendar_date) NOT IN (0, 6) THEN 1 ELSE 0 END AS is_workingday
FROM date_series d
CROSS JOIN plants p
