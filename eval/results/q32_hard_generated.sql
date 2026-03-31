SELECT
  s.asin,
  MAX(s.item_name) AS item_name,
  SUM(s.product_gms) AS revenue
FROM shipped_raw s
GROUP BY s.asin
ORDER BY revenue DESC
LIMIT 10;