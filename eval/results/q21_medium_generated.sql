SELECT
  s.year,
  ((s.month - 1) / 3 + 1) AS quarter,
  SUM(s.product_gms) AS total_sales
FROM shipped_raw s
GROUP BY
  s.year,
  ((s.month - 1) / 3 + 1)
ORDER BY
  s.year,
  quarter;