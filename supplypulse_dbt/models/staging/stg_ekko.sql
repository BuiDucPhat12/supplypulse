WITH source AS (
    SELECT * FROM {{ source('bronze', 'EKKO') }}
),

renamed AS (
    SELECT
        ebeln                       AS po_number,
        lifnr                       AS vendor_number,
        ekorg                       AS purchasing_org,
        ekgrp                       AS purchasing_group,
        bsart                       AS po_type,
        bedat::date                 AS po_date,
        waers                       AS currency,
        loekz                       AS deletion_flag,
        statu                       AS status,
        inco1                       AS incoterms_1,
        inco2                       AS incoterms_2
    FROM source
)

SELECT * FROM renamed
