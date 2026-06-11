SELECT
    quota_arrangement_number,
    material_number,
    plant,
    valid_from,
    valid_to,
    total_released_quantity
FROM {{ ref('stg_equk') }}
WHERE CURRENT_DATE BETWEEN valid_from AND valid_to
