-- TT + quota per material × vendor. max_tt = TT của vendor chậm nhất cho material
-- — mart_shortage_report dùng để tính end_of_tt_gr.
WITH per_vendor AS (
    SELECT
        marc_id,
        vendor_number,
        MAX(transit_time_days) AS transit_time_days,
        MAX(quote_percent)     AS quote_percent
    FROM {{ ref('int_purchasing_document_tt') }}
    GROUP BY marc_id, vendor_number
)

SELECT
    *,
    MAX(transit_time_days) OVER (PARTITION BY marc_id) AS max_tt
FROM per_vendor
