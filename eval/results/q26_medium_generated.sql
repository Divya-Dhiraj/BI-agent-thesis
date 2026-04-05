SELECT
  s.year,
  s.month,
  SUM(s.shipped_units) AS shipped_units,
  SUM(s.product_gms) AS product_gms,
  SUM(s.shipped_cogs) AS shipped_cogs
FROM shipped_raw s
WHERE s.item_name ILIKE '%Google Pixel%'
GROUP BY
  s.year,
  s.month
ORDER BY
  s.year,
  s.month;