SELECT
  SUM(s.product_gms) AS total_sales_gms
FROM shipped_raw s
WHERE s.brand_name ILIKE '%Sony%';