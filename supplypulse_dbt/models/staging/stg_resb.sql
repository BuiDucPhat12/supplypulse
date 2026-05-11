WITH source AS (
    SELECT * FROM {{ source('bronze', 'RESB') }}
),

renamed AS (
    SELECT
        rsnum                           AS reservation_number,
        rspos                           AS reservation_item,
        rsart                           AS reservation_type,
        matnr                           AS material_number,
        werks                           AS plant,
        lgort                           AS storage_location,
        aufnr                           AS order_number,
        vbeln                           AS sales_order_number,
        bddat::date                     AS requirement_date,
        CAST(bdmng AS numeric(10,2))    AS required_quantity,
        CAST(enmng AS numeric(10,2))    AS withdrawn_quantity,
        meins                           AS unit_of_measure,
        kzear                           AS final_issue_flag
    FROM source
)

SELECT * FROM renamed
