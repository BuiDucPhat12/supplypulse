WITH source AS (
    SELECT * FROM {{ source('bronze', 'EKPO') }}
),

renamed AS (
    SELECT
        ebeln || '-' || ebelp       AS ekpo_id,
        matnr || '-' || werks       AS marc_id,
        ebeln                       AS po_number,
        ebelp                       AS po_item,
        matnr                       AS material_number,
        werks                       AS plant,
        matkl                       AS material_group,
        CAST(menge AS numeric(10,2)) AS order_quantity,
        meins                       AS unit_of_measure,
        CAST(netpr AS numeric(10,2)) AS net_price,
        CAST(netwr AS numeric(10,2)) AS net_value,
        pstyp                       AS item_category,
        loekz                       AS deletion_flag,
        elikz                       AS delivery_completed_flag
    FROM source
)

SELECT * FROM renamed
