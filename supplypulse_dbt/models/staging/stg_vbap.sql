    WITH source AS (
    SELECT * FROM {{ source('bronze', 'VBAP') }}
    ),
    renamed AS (
    SELECT
        VBELN AS sales_order_number,
        POSNR AS sales_order_item,
        MATNR AS material_number,
        CAST(MENGE AS numeric(10,2)) AS order_quantity,
        MEINS AS order_unit,
        CAST(NETWR AS numeric(10,2)) AS net_value,
        WAERK AS currency,
        WERKS AS plant,
        LGORT AS storage_location,
        PSTYV AS item_category,
        ABGRU AS rejection_reason,
        ERDAT::date AS created_date
    FROM source
)
SELECT * FROM renamed
