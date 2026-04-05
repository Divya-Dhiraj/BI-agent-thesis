SELECT
  asp_bucket,
  SUM(product_gms)   AS total_sales,
  SUM(shipped_units) AS total_shipped_units
FROM shipped_raw
GROUP BY asp_bucket
ORDER BY asp_bucket;