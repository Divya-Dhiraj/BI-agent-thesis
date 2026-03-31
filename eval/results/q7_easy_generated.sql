SELECT
  SUM(s.product_gms) AS total_sales_gms,
  SUM(s.shipped_units) AS total_shipped_units
FROM shipped_raw s
WHERE s.brand_name ILIKE '%Sony%';