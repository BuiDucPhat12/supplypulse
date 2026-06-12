WITH source AS (
    SELECT * FROM {{ source('bronze', 'EKET') }}
),

renamed AS (
    SELECT
        ebeln || '-' || ebelp           AS ekpo_id,
        ebeln                           AS po_number,
        ebelp                           AS po_item,
        etenr                           AS schedule_line_number,
        eindt::date                     AS delivery_date,
        mbdat::date                     AS goods_receipt_date,
        wadat::date                     AS planned_delivery_date,
        CAST(menge AS numeric(10,2))    AS scheduled_quantity,
        CAST(wemng AS numeric(10,2))    AS goods_receipt_quantity,
        -- open_quantity not in bronze: calculated at intermediate layer as menge - wemng
        CAST(menge AS numeric(10,2))
            - CAST(wemng AS numeric(10,2)) AS open_quantity
    FROM source
)

SELECT * FROM renamed
