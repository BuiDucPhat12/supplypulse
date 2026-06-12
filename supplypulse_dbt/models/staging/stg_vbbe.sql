WITH source_data AS (
    SELECT * FROM {{ source('bronze', 'VBBE') }}
),

renamed AS (
    SELECT
        vbeln                       AS sales_order_number,
        posnr                       AS sales_order_item,
        matnr                       AS material_number,
        werks                       AS plant,
        bdart                       AS requirement_type,
        auart                       AS sales_document_type,
        kunnr                       AS customer_number,
        mbdat::date                 AS requirement_date,
        omeng::numeric              AS open_requirement_qty,
        vmeng::numeric              AS confirmed_qty,
        meins                       AS unit_of_measure
    FROM source_data
)

SELECT * FROM renamed
