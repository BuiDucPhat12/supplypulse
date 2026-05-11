WITH source AS (
    SELECT * FROM {{ source('bronze', 'TFACT') }}
),

renamed AS (
    SELECT
        ident                           AS calendar_id,
        spras                           AS language,
        ltext                           AS calendar_name
    FROM source
)

SELECT * FROM renamed
