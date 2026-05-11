WITH source AS (
    SELECT * FROM {{ source('bronze', 'LFA1') }}
),

renamed AS (
    SELECT
        lifnr                           AS vendor_id,
        lifnr                           AS vendor_number,
        name1                           AS vendor_name,
        land1                           AS country,
        ort01                           AS city,
        regio                           AS region,
        erdat::date                     AS created_date,
        sperr                           AS payment_block_flag
    FROM source
)

SELECT * FROM renamed
