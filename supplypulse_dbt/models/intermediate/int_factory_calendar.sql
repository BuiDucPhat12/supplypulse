-- Range động: 750 ngày lùi (cover historical LIKP dates, data v2 history = 730d)
-- + 200 ngày tới (cover future window 180d của data v2)
WITH date_series AS (
    SELECT generate_series(
        CURRENT_DATE - INTERVAL '750 days',
        CURRENT_DATE + INTERVAL '200 days',
        INTERVAL '1 day'
    )::date AS calendar_date
),

plants AS (
    SELECT plant, factory_calendar_key
    FROM {{ ref('stg_t001w') }}
),

flagged AS (
    SELECT
        p.plant,
        p.factory_calendar_key,
        d.calendar_date,
        CASE WHEN EXTRACT(DOW FROM d.calendar_date) NOT IN (0, 6) THEN 1 ELSE 0 END AS is_workingday,
        -- Snap cuối tuần sang Monday kế tiếp; working day giữ nguyên
        CASE EXTRACT(DOW FROM d.calendar_date)
            WHEN 6 THEN d.calendar_date + 2
            WHEN 0 THEN d.calendar_date + 1
            ELSE d.calendar_date
        END AS jump_to_wd_date
    FROM date_series d
    CROSS JOIN plants p
)

SELECT
    plant,
    factory_calendar_key,
    calendar_date,
    is_workingday,
    jump_to_wd_date,
    -- Cumulative working days: với mọi working day, bằng working_day_index của int_working_calendar
    SUM(is_workingday) OVER (PARTITION BY plant ORDER BY calendar_date) AS technical_day_number
FROM flagged
