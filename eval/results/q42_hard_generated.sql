SELECT
  s.asin,
  s.item_name,
  SUM(s.product_gms) AS revenue
FROM shipped_raw s
WHERE s.item_name ILIKE '%iphone%'
GROUP BY
  s.asin,
  s.item_name
ORDER BY revenue DESC
LIMIT 5;