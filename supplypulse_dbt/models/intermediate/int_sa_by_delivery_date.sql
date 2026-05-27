WITH eket AS (
    SELECT * FROM {{ ref('stg_eket') }}
),

aggregated AS (
    SELECT
        ekpo_id,
        po_number,
        po_item,
        delivery_date,
        MIN(goods_receipt_date)         AS goods_receipt_date,
        SUM(scheduled_quantity)         AS scheduled_quantity,
        SUM(goods_receipt_quantity)     AS goods_receipt_quantity,
        SUM(open_quantity)              AS open_quantity
    FROM eket
    GROUP BY ekpo_id, po_number, po_item, delivery_date
)

SELECT * FROM aggregated
