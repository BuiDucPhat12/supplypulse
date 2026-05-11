WITH source AS (
    SELECT * FROM {{ source('bronze', 'EQUP') }}
),

renamed AS (
    SELECT
        qunum                           AS quota_arrangement_number,
        qupos                           AS quota_item,
        lifnr                           AS vendor_number,
        beskz                           AS procurement_type,
        CAST(quote AS numeric(10,2))    AS quota,
        CAST(qumng AS numeric(10,2))    AS quota_usage_quantity,
        CAST(plifz AS numeric(10,2))    AS planned_delivery_days
    FROM source
)

SELECT * FROM renamed
