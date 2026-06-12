WITH equk AS (
    SELECT * FROM {{ ref('int_equk_active') }}
),

equp AS (
    SELECT * FROM {{ ref('int_equp_active') }}
),

lfa1 AS (
    SELECT * FROM {{ ref('stg_lfa1') }}
),

joined AS (
    SELECT
        equk.quota_arrangement_number,
        equk.material_number,
        equk.plant,
        equk.valid_from,
        equk.valid_to,
        equp.quota_item,
        equp.vendor_number,
        lfa1.vendor_name,
        lfa1.country,
        equp.procurement_type,
        equp.quota,
        equp.planned_delivery_days,
        equp.quota / NULLIF(SUM(equp.quota) OVER (PARTITION BY equk.quota_arrangement_number), 0) AS quote_percent
    FROM equk
    INNER JOIN equp ON equk.quota_arrangement_number = equp.quota_arrangement_number
    LEFT JOIN lfa1 ON equp.vendor_number = lfa1.vendor_number
)

SELECT * FROM joined
