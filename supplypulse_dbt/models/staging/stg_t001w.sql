WITH source AS (
    SELECT * FROM {{ source('bronze', 'T001W') }}
),

renamed AS (
    SELECT
        werks                           AS plant,
        name1                           AS plant_name,
        fabkl                           AS factory_calendar_key,
        ekorg                           AS purchasing_org,
        land1                           AS country,
        ort01                           AS city
    FROM source
)

SELECT * FROM renamed
