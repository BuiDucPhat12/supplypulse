WITH raw_demand AS (
    SELECT
        reservation_number  AS customer_order,
        reservation_item    AS co_item,
        reservation_type    AS requirement_type,
        material_number || '-' || plant AS marc_id,
        material_number,
        plant,
        requirement_date,
        required_quantity - withdrawn_quantity AS demand_qty,
        'RESB'              AS demand_source
    FROM {{ ref('stg_resb') }}
    WHERE required_quantity - withdrawn_quantity > 0

    UNION ALL

    SELECT
        sales_order_number  AS customer_order,
        sales_order_item    AS co_item,
        requirement_type,
        material_number || '-' || plant AS marc_id,
        material_number,
        plant,
        requirement_date,
        open_requirement_qty AS demand_qty,
        'VBBE'              AS demand_source
    FROM {{ ref('stg_vbbe') }}
),

demand_with_key AS (
    SELECT raw_demand.*
    FROM raw_demand
    INNER JOIN {{ ref('int_material_bbm') }} imb ON raw_demand.marc_id = imb.marc_id
),

overdue_per_pn AS (
    SELECT
        marc_id,
        COALESCE(SUM(demand_qty) FILTER (WHERE requirement_date < DATE '2024-09-01'), 0) AS backlog_per_pn
    FROM demand_with_key
    GROUP BY marc_id
),

overdue_per_pn_contype AS (
    SELECT
        marc_id,
        demand_source,
        requirement_type,
        COALESCE(SUM(demand_qty) FILTER (WHERE requirement_date < DATE '2024-09-01'), 0) AS backlog_per_pn_contype
    FROM demand_with_key
    GROUP BY marc_id, demand_source, requirement_type
),

future_with_overdue AS (
    SELECT
        d.marc_id,
        d.customer_order,
        d.co_item,
        d.demand_source,
        d.requirement_type,
        d.material_number,
        d.plant,
        d.requirement_date,
        d.demand_qty,
        COALESCE(pn.backlog_per_pn, 0)           AS backlog_per_pn,
        COALESCE(ct.backlog_per_pn_contype, 0)   AS backlog_per_pn_contype
    FROM demand_with_key d
    LEFT JOIN overdue_per_pn pn
        ON d.marc_id = pn.marc_id
    LEFT JOIN overdue_per_pn_contype ct
        ON d.marc_id = ct.marc_id
        AND d.demand_source = ct.demand_source
        AND d.requirement_type = ct.requirement_type
    WHERE d.requirement_date BETWEEN DATE '2024-09-01' AND DATE '2024-09-01' + INTERVAL '120 days'
),

null_rows AS (
    SELECT
        pn.marc_id,
        NULL                AS customer_order,
        NULL                AS co_item,
        NULL                AS demand_source,
        NULL                AS requirement_type,
        NULL                AS material_number,
        NULL                AS plant,
        NULL::date          AS requirement_date,
        NULL::numeric       AS demand_qty,
        pn.backlog_per_pn,
        0                   AS backlog_per_pn_contype
    FROM overdue_per_pn pn
    WHERE pn.backlog_per_pn > 0
      AND NOT EXISTS (
          SELECT 1
          FROM demand_with_key d
          WHERE d.marc_id = pn.marc_id
            AND d.requirement_date >= DATE '2024-09-01'
      )
)

SELECT * FROM future_with_overdue
UNION ALL
SELECT * FROM null_rows
