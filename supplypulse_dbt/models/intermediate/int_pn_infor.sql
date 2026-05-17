WITH mard_agg AS (
    SELECT
        material_number,
        plant,
        COALESCE(SUM(unrestricted_stock), 0)      AS available_stock,
        COALESCE(SUM(blocked_stock), 0)            AS blocked_stock_s,
        COALESCE(SUM(quality_inspection_stock), 0) AS blocked_stock_q
    FROM {{ ref('stg_mard') }}
    GROUP BY material_number, plant
),

final AS (
    SELECT
        m.marc_id,
        m.material_number,
        m.plant,
        m.gr_processing_days,
        m.safety_stock,
        m.procurement_type,
        m.mrpc,
        m.reorder_point,
        m.abc_indicator,
        m.planned_delivery_days,
        m.purchasing_group,
        COALESCE(d.available_stock, 0)  AS available_stock,
        COALESCE(d.blocked_stock_s, 0)  AS blocked_stock_s,
        COALESCE(d.blocked_stock_q, 0)  AS blocked_stock_q
    FROM {{ ref('int_material_bbm') }} AS m
    LEFT JOIN mard_agg AS d
        ON m.material_number = d.material_number
        AND m.plant = d.plant
)

SELECT * FROM final
