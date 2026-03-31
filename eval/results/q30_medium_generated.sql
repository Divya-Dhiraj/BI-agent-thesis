SELECT
  s.brand_name,
  SUM(s.shipped_cogs) AS total_cogs
FROM shipped_raw s
WHERE s.year = 2024
GROUP BY s.brand_name
ORDER BY total_cogs DESC
LIMIT 5;