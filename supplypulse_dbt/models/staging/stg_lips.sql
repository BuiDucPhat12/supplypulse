WITH source AS (
    SELECT * FROM {{ source('bronze', 'LIPS') }}
),

renamed AS (
    SELECT
        vbeln                           AS delivery_number,
        posnr                           AS delivery_item,
        matnr                           AS material_number,
        matkl                           AS material_group,
        werks                           AS plant,
        lgort                           AS storage_location,
        vgbel                           AS reference_document,
        vgpos                           AS reference_item,
        bwart                           AS movement_type,
        mbdat::date                     AS goods_receipt_date,
        CAST(lfimg AS numeric(10,2))    AS delivery_quantity,
        CAST(netwr AS numeric(10,2))    AS net_value,
        meins                           AS unit_of_measure
    FROM source
)

SELECT * FROM renamed
