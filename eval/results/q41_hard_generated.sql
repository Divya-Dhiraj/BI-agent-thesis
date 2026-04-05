WITH s AS (
  SELECT
    CAST(asin AS TEXT) AS asin,
    MAX(item_name) AS item_name,
    year,
    month,
    SUM(shipped_units) AS shipped_units
  FROM shipped_raw
  WHERE (brand_name ILIKE '%Samsung%' OR item_name ILIKE '%Samsung%')
  GROUP BY CAST(asin AS TEXT), year, month
),
c AS (
  SELECT
    CAST(asin AS TEXT) AS asin,
    mapped_year AS year,
    mapped_month AS month,
    SUM(conceded_units) AS conceded_units
  FROM concession_raw
  WHERE (brand_name ILIKE '%Samsung%' OR item_name ILIKE '%Samsung%')
  GROUP BY CAST(asin AS TEXT), mapped_year, mapped_month
),
by_asin AS (
  SELECT
    s.asin,
    MAX(s.item_name) AS item_name,
    SUM(s.shipped_units) AS shipped_units,
    SUM(COALESCE(c.conceded_units, 0)) AS conceded_units
  FROM s
  LEFT JOIN c
    ON c.asin = s.asin
   AND c.year = s.year
   AND c.month = s.month
  GROUP BY s.asin
)
SELECT
  asin,
  item_name,
  shipped_units,
  conceded_units,
  ROUND((conceded_units * 100.0) / NULLIF(shipped_units, 0), 2) AS return_rate_pct
FROM by_asin
WHERE shipped_units > 0
ORDER BY return_rate_pct DESC, conceded_units DESC
LIMIT 50;