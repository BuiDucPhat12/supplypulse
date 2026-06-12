WITH vbak AS (
SELECT * FROM {{ source('bronze', 'VBAK') }}
),

renamed_vbak AS (

SELECT
    vbak.vbeln AS sales_order_id,
    vbak.erdat::date AS created_date,
    vbak.erzet AS created_time,
    vbak.ernam AS created_by,
    vbak.auart AS sales_document_type,
    vbak.kunnr AS customer_number,
    vbak.netwr AS net_value,
    vbak.waerk AS currency,
    vbak.vkorg AS sales_organization,
    vbak.vtweg AS distribution_channel,
    vbak.spart AS division,
    vbak.gbstk AS delivery_status
FROM vbak)

SELECT * FROM renamed_vbak
