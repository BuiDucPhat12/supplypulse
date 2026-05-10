WITH source_data AS (
SELECT * FROM {{source('bronze', 'VBUP')}}
),
renamed_vbup AS (
SELECT
    source_data.vbeln AS sales_order_id,
    source_data.posnr AS item_number,
    source_data.gbsta AS overall_status,
    source_data.abstk AS delivery_block,
    source_data.WBSTK AS picking_status,
    source_data.FKSTK AS billing_status,
    source_data.LVSTK AS goods_movement_status,
    source_data.LSSTK AS final_delivery_status,
    source_data.KOSTA AS cost_status,
    source_data.LFGSK AS credit_status
FROM source_data
)
SELECT * FROM renamed_vbup
