-- Hợp nhất future supply: SA open lines ('Order Qty') + ASN đang trên đường ('ASN').
-- ASN 'overdue' KHÔNG vào đây — đã quá hạn, không phải future supply;
-- được xử lý riêng qua asn_total_due_qty ở mart_inventory_simulation.
SELECT
    'Order Qty' AS supply_type,
    marc_id,
    material_number,
    plant,
    vendor_number,
    vendor_name,
    country,
    planned_availability_date,
    open_quantity      AS order_qty,
    order_qty_due,
    cumulative_asn_qty AS fulfill_qty
FROM {{ ref('int_sa_late_shipment') }}

UNION ALL

SELECT
    'ASN' AS supply_type,
    marc_id,
    material_number,
    plant,
    vendor_number,
    vendor_name,
    country,
    planned_availability_date,
    delivery_quantity  AS order_qty,
    asn_total_due_qty  AS order_qty_due,
    NULL::numeric      AS fulfill_qty
FROM {{ ref('int_inbound_deliveries_asn') }}
WHERE asn_status = 'future'
