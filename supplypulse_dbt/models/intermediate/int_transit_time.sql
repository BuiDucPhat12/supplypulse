SELECT
    stt.lifnr AS vendor_number,
    stt.ekorg AS purchasing_org,
    stt.werks AS plant,
    lfa1.vendor_name,
    lfa1.country,
    t001w.plant_name,
    t001w.factory_calendar_key,
    stt.transit_time_days
FROM {{ ref('seed_transit_time') }} stt
LEFT JOIN {{ ref('stg_lfa1') }} lfa1 ON stt.lifnr = lfa1.vendor_number
LEFT JOIN {{ ref('stg_t001w') }} t001w ON stt.werks = t001w.plant
