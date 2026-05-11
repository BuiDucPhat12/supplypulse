WITH source AS (
SELECT * FROM {{source('bronze', 'MARD')}}
),
renamed AS (
SELECT
    matnr AS material_number,
    werks AS plant,
    lgort AS storage_location,
    CAST(labst AS numeric(10,2)) AS unrestricted_stock,
    CAST(insme AS numeric(10,2)) AS quality_inspection_stock,
    CAST(speme AS numeric(10,2)) AS blocked_stock,
    CAST(umlme AS numeric(10,2)) AS transfer_stock
FROM source)
SELECT * FROM renamed
