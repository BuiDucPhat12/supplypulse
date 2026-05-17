WITH source AS (
SELECT * FROM {{ ref('stg_marc') }}
)
SELECT
    marc_id,
    material_number,
    plant,
    mrpc,
    procurement_type,
    gr_processing_days,
    safety_stock,
    reorder_point,
    abc_indicator,
    planned_delivery_days,
    purchasing_group
FROM source
