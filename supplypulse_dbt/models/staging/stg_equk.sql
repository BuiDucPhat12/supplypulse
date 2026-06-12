WITH source AS (
    SELECT * FROM {{ source('bronze', 'EQUK') }}
),

renamed AS (
    SELECT
        matnr                           AS material_number,
        werks                           AS plant,
        qunum                           AS quota_arrangement_number,
        vdatu::date                     AS valid_from,
        bdatu::date                     AS valid_to,
        erdat::date                     AS created_date,
        CAST(scmng AS numeric(10,2))    AS total_released_quantity
    FROM source
)

SELECT * FROM renamed
