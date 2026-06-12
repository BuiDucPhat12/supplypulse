WITH source AS (
    SELECT * FROM {{ source('bronze', 'LIKP') }}
),

renamed AS (
    SELECT
        vbeln                           AS delivery_number,
        lfart                           AS delivery_type,
        kunnr                           AS customer_number,
        vkorg                           AS sales_org,
        route                           AS route,
        erdat::date                     AS created_date,
        lfdat::date                     AS planned_delivery_date,
        wadat::date                     AS planned_goods_issue_date,
        wadat_ist::date                 AS actual_goods_issue_date,
        CAST(netwr AS numeric(10,2))    AS net_value,
        waerk                           AS currency
    FROM source
)

SELECT * FROM renamed
