WITH likp AS (
    SELECT * FROM {{ ref('stg_likp') }}
),

lips AS (
    SELECT * FROM {{ ref('stg_lips') }}
),

vbup AS (
    SELECT * FROM {{ ref('stg_vbup') }}
),

marc AS (
    SELECT * FROM {{ ref('stg_marc') }}
),

joined AS (
    SELECT
        likp.delivery_number,
        likp.delivery_type,
        likp.created_date,
        likp.planned_delivery_date          AS planned_delivery_date_hdr,
        likp.actual_goods_issue_date,
        -- budat_mkpf equivalent: earliest of created_date and actual_goods_issue_date
        -- actual_goods_issue_date is NULL for pending deliveries → fallback to created_date
        COALESCE(
            LEAST(likp.created_date, likp.actual_goods_issue_date),
            likp.created_date
        )                                   AS gr_date,
        lips.delivery_item,
        lips.material_number,
        lips.plant,
        lips.material_group,
        lips.storage_location,
        lips.reference_document,
        lips.reference_item,
        lips.movement_type,
        lips.goods_receipt_date,
        lips.delivery_quantity,
        lips.unit_of_measure,
        vbup.goods_movement_status,
        marc.marc_id,
        marc.gr_processing_days
    FROM likp
    INNER JOIN lips ON likp.delivery_number = lips.delivery_number
    LEFT JOIN vbup
        ON  lips.delivery_number = vbup.document_number
        AND lips.delivery_item   = vbup.document_item
    LEFT JOIN marc
        ON  lips.material_number = marc.material_number
        AND lips.plant           = marc.plant
)

SELECT * FROM joined
