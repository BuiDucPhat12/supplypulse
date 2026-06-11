SELECT marc_id, vendor_number, max_tt
FROM {{ ref('int_tt_quota') }}
WHERE max_tt < 0
