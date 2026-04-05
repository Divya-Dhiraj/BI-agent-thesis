SELECT
  s.year,
  s.month,
  SUM(s.shipped_units) AS total_shipped_units,
  SUM(s.product_gms)   AS total_sales_gms
FROM shipped_raw s
WHERE s.item_name ILIKE '%iPhone%'
GROUP BY
  s.year,
  s.month
ORDER BY
  s.year,
  s.month;