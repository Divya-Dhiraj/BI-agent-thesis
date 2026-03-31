WITH sales AS (
  SELECT
    CAST(asin AS TEXT) AS asin,
    MAX(item_name) AS item_name,
    SUM(shipped_units) AS shipped_units
  FROM shipped_raw
  GROUP BY 1
),
returns AS (
  SELECT
    CAST(asin AS TEXT) AS asin,
    SUM(conceded_units) AS conceded_units
  FROM concession_raw
  GROUP BY 1
)
SELECT
  s.asin,
  s.item_name,
  s.shipped_units,
  COALESCE(r.conceded_units, 0) AS conceded_units,
  (COALESCE(r.conceded_units, 0) * 100.0) / NULLIF(s.shipped_units, 0) AS return_rate_pct
FROM sales s
LEFT JOIN returns r
  ON r.asin = s.asin
WHERE s.shipped_units > 0
ORDER BY return_rate_pct DESC NULLS LAST, s.shipped_units DESC
LIMIT 10;