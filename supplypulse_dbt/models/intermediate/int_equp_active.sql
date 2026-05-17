SELECT
    quota_arrangement_number,
    quota_item,
    vendor_number,
    procurement_type,
    quota,
    quota_usage_quantity,
    planned_delivery_days
FROM {{ ref('stg_equp') }}
