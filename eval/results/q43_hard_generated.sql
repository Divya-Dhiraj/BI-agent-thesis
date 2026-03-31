WITH shipped AS (
  SELECT
    s.year,
    s.month,
    SUM(CASE WHEN s.item_name ILIKE '%Pixel%'  THEN s.shipped_units ELSE 0 END) AS pixel_shipped_units,
    SUM(CASE WHEN s.item_name ILIKE '%iPhone%' THEN s.shipped_units ELSE 0 END) AS iphone_shipped_units
  FROM shipped_raw s
  WHERE s.item_name ILIKE '%Pixel%'
     OR s.item_name ILIKE '%iPhone%'
  GROUP BY 1, 2
),
conceded AS (
  SELECT
    c.mapped_year AS year,
    c.mapped_month AS month,
    SUM(CASE WHEN c.item_name ILIKE '%Pixel%'  THEN c.conceded_units ELSE 0 END) AS pixel_conceded_units,
    SUM(CASE WHEN c.item_name ILIKE '%iPhone%' THEN c.conceded_units ELSE 0 END) AS iphone_conceded_units
  FROM concession_raw c
  WHERE c.item_name ILIKE '%Pixel%'
     OR c.item_name ILIKE '%iPhone%'
  GROUP BY 1, 2
)
SELECT
  COALESCE(s.year, c.year)  AS mapped_year,
  COALESCE(s.month, c.month) AS mapped_month,

  s.pixel_shipped_units,
  c.pixel_conceded_units,
  (c.pixel_conceded_units * 100.0) / NULLIF(s.pixel_shipped_units, 0) AS pixel_return_rate_pct,

  s.iphone_shipped_units,
  c.iphone_conceded_units,
  (c.iphone_conceded_units * 100.0) / NULLIF(s.iphone_shipped_units, 0) AS iphone_return_rate_pct
FROM shipped s
FULL OUTER JOIN conceded c
  ON c.year = s.year
 AND c.month = s.month
ORDER BY 1, 2;