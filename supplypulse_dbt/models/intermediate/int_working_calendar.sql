SELECT
    plant,
    factory_calendar_key,
    calendar_date,
    ROW_NUMBER() OVER (PARTITION BY plant ORDER BY calendar_date) AS working_day_index
FROM {{ ref('int_factory_calendar') }}
WHERE is_workingday = 1
