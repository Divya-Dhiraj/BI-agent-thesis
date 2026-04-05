SELECT
  fulfillment_channel,
  SUM(product_gms)    AS total_sales,
  SUM(shipped_units)  AS total_units
FROM shipped_raw
GROUP BY fulfillment_channel
ORDER BY total_sales DESC;