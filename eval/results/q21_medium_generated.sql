SELECT
  year,
  ((month - 1) / 3 + 1) AS quarter,
  SUM(product_gms) AS total_sales_gms,
  SUM(shipped_units) AS total_shipped_units
FROM shipped_raw
GROUP BY
  year,
  ((month - 1) / 3 + 1)
ORDER BY
  year,
  quarter;