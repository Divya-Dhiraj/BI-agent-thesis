SELECT
  SUM(product_gms) AS total_sales_gms,
  SUM(shipped_units) AS total_shipped_units
FROM shipped_raw;