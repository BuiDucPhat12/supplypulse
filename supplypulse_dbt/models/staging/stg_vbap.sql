    WITH source_data AS (
    SELECT * FROM {{ source('bronze', 'VBAP') }}
    ),
    renamed_vbap AS (
    SELECT
        VBELN AS sales_order_number,
        POSNR AS sales_order_item,
        MATNR AS material_number,
        MENGE AS order_quantity,
        MEINS AS order_unit,
        NETWR AS net_value,
        WAERK AS currency,
        WERKS AS plant,
        LGORT AS storage_location,
        PSTYV AS item_category,
        ABGRU AS rejection_reason
    FROM source_data
)
SELECT * FROM renamed_vbap
