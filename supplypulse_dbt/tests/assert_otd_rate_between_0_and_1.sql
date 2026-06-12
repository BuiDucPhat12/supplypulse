-- otd_rate là tỷ lệ — ngoài [0,1] nghĩa là logic đếm on_time/completed sai
SELECT vendor_number, otd_rate
FROM {{ ref('mart_vendor_performance') }}
WHERE otd_rate < 0 OR otd_rate > 1
