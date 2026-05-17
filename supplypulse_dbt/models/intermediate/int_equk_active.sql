SELECT
    quota_arrangement_number,
    material_number,
    plant,
    valid_from,
    valid_to,
    total_released_quantity
FROM {{ ref('stg_equk') }}
WHERE DATE '2024-09-01' BETWEEN valid_from AND valid_to
