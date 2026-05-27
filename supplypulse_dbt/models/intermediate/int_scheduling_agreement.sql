WITH pd AS (
    SELECT * FROM {{ ref('int_purchasing_document_active') }}
),

sa_by_date AS (
    SELECT * FROM {{ ref('int_sa_by_delivery_date') }}
),

joined AS (
    SELECT
        pd.po_number,
        pd.vendor_number,
        pd.purchasing_org,
        pd.po_type,
        pd.po_date,
        pd.marc_id,
        pd.material_number,
        pd.plant,
        sa.ekpo_id,
        sa.po_item,
        sa.delivery_date,
        sa.goods_receipt_date,
        sa.scheduled_quantity,
        sa.goods_receipt_quantity,
        sa.open_quantity
    FROM pd
    INNER JOIN sa_by_date sa ON pd.ekpo_id = sa.ekpo_id
)

SELECT * FROM joined
