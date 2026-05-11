WITH source AS (
SELECT * FROM {{ source('bronze', 'MARC') }}
),
renamed AS (
SELECT
    matnr || '-' || werks AS marc_id,
    matnr AS material_number,
    werks AS plant,
    dispo AS mrpc,
    beskz as procurement_type,
    CAST(webaz AS numeric(10,2)) AS gr_processing_days,
    CAST(EISBE AS numeric(10,2)) AS safety_stock,
    CAST(MINBE AS numeric(10,2)) AS reorder_point,
    MAABC AS abc_indicator,
    CAST(PLIFZ AS numeric(10,2)) AS planned_delivery_days,
    EKGRP AS purchasing_group
FROM source)
SELECT * FROM renamed
