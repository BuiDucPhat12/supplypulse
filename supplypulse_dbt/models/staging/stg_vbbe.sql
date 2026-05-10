        WITH source_data AS (
        SELECT * FROM {{source('bronze', 'VBBE')}}
    ),
    renamed_vbbe AS (
        SELECT
            MATNR AS material_number,
            WERKS AS plant,
            LGORT AS storage_location,
            BDART AS requirement_type,
            VBELN AS sales_order_number,
            POSNR AS sales_order_item,
            BDMNG AS requirement_quantity,
            MEINS AS requirement_unit,
            BDDAT AS requirement_date,
            AEDAT AS last_change_date
        FROM source_data
)
SELECT * FROM renamed_vbbe
