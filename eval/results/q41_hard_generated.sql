WITH samsung_sales AS (
  SELECT
    CAST(s.asin AS TEXT) AS asin,
    MAX(s.item_name) AS item_name,
    s.year,
    s.month,
    SUM(s.shipped_units) AS shipped_units
  FROM shipped_raw s
  WHERE (s.brand_name ILIKE '%Samsung%' OR s.item_name ILIKE '%Samsung%')
  GROUP BY CAST(s.asin AS TEXT), s.year, s.month
),
samsung_returns AS (
  SELECT
    CAST(c.asin AS TEXT) AS asin,
    c.mapped_year AS year,
    c.mapped_month AS month,
    SUM(c.conceded_units) AS conceded_units
  FROM concession_raw c
  WHERE (c.brand_name ILIKE '%Samsung%' OR c.item_name ILIKE '%Samsung%')
  GROUP BY CAST(c.asin AS TEXT), c.mapped_year, c.mapped_month
),
asin_month AS (
  SELECT
    s.asin,
    s.item_name,
    s.year,
    s.month,
    s.shipped_units,
    COALESCE(r.conceded_units, 0) AS conceded_units
  FROM samsung_sales s
  LEFT JOIN samsung_returns r
    ON r.asin = s.asin
   AND r.year = s.year
   AND r.month = s.month
),
asin_rollup AS (
  SELECT
    asin,
    MAX(item_name) AS item_name,
    SUM(shipped_units) AS shipped_units,
    SUM(conceded_units) AS conceded_units,
    (SUM(conceded_units) * 100.0) / NULLIF(SUM(shipped_units), 0) AS return_rate_pct
  FROM asin_month
  GROUP BY asin
)
SELECT
  asin,
  item_name,
  shipped_units,
  conceded_units,
  return_rate_pct
FROM asin_rollup
WHERE shipped_units > 0
ORDER BY return_rate_pct DESC, conceded_units DESC
LIMIT 50;