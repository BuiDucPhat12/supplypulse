SELECT
    ekpo.ekpo_id,
    ekko.po_number,
    ekko.vendor_number,
    ekko.purchasing_org,
    ekpo.po_item,
    ekpo.material_number || '-' || ekpo.plant AS marc_id,
    ekpo.material_number,
    ekpo.plant,
    ekko.po_type,
    ekko.po_date,
    ekpo.order_quantity
FROM {{ ref('stg_ekko') }} ekko
INNER JOIN {{ ref('stg_ekpo') }} ekpo ON ekko.po_number = ekpo.po_number
WHERE COALESCE(ekko.deletion_flag, '') NOT IN ('L', 'S', 'X')
    AND COALESCE(ekpo.deletion_flag, '') NOT IN ('L', 'S', 'X')
