-- Late shipment = SA line mà ASN từ cùng vendor chưa cover đủ open quantity,
-- VÀ vẫn còn trong transit-time window (hàng còn có thể đang trên đường).
-- Nếu đã qua TT window mà thiếu → đó là shortage thực sự, không phải late shipment.
WITH sa AS (
    SELECT * FROM {{ ref('int_sa_future') }}
),

asn AS (
    SELECT * FROM {{ ref('int_inbound_deliveries_asn') }}
    WHERE asn_status = 'future'
),

with_cumulative AS (
    SELECT
        sa.*,
        -- Tổng ASN cùng vendor + material có PAD <= PAD của SA line này
        COALESCE((
            SELECT SUM(a.delivery_quantity)
            FROM asn a
            WHERE a.marc_id = sa.marc_id
              AND a.vendor_number = sa.vendor_number
              AND a.planned_availability_date <= sa.planned_availability_date
        ), 0) AS cumulative_asn_qty
    FROM sa
)

SELECT
    *,
    open_quantity - cumulative_asn_qty AS order_qty_due,
    CASE
        WHEN delivery_date + COALESCE(transit_time_days, 0)::int >= CURRENT_DATE
         AND open_quantity - cumulative_asn_qty > 0
        THEN 1 ELSE 0
    END AS late_shipment_flag
FROM with_cumulative
