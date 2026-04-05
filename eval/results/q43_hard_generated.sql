WITH shipped AS (
  SELECT
    s.year,
    s.month,
    CASE
      WHEN s.item_name ILIKE '%pixel%' THEN 'Google Pixel'
      WHEN s.item_name ILIKE '%iphone%' THEN 'iPhone'
    END AS product_line,
    SUM(s.shipped_units) AS shipped_units
  FROM shipped_raw s
  WHERE s.item_name ILIKE '%pixel%'
     OR s.item_name ILIKE '%iphone%'
  GROUP BY 1,2,3
),
conceded AS (
  SELECT
    c.mapped_year AS year,
    c.mapped_month AS month,
    CASE
      WHEN c.item_name ILIKE '%pixel%' THEN 'Google Pixel'
      WHEN c.item_name ILIKE '%iphone%' THEN 'iPhone'
    END AS product_line,
    SUM(c.conceded_units) AS conceded_units
  FROM concession_raw c
  WHERE c.item_name ILIKE '%pixel%'
     OR c.item_name ILIKE '%iphone%'
  GROUP BY 1,2,3
)
SELECT
  s.product_line,
  s.year,
  s.month,
  SUM(s.shipped_units) AS shipped_units,
  COALESCE(SUM(c.conceded_units), 0) AS conceded_units,
  (COALESCE(SUM(c.conceded_units), 0) * 100.0) / NULLIF(SUM(s.shipped_units), 0) AS return_rate_pct
FROM shipped s
LEFT JOIN conceded c
  ON c.product_line = s.product_line
 AND c.year = s.year
 AND c.month = s.month
GROUP BY 1,2,3
ORDER BY s.year, s.month, s.product_line;