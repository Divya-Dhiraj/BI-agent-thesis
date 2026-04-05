WITH s AS (
  SELECT
    brand_name,
    SUM(shipped_units) AS shipped_units
  FROM shipped_raw
  GROUP BY 1
),
c AS (
  SELECT
    c.brand_name,
    SUM(c.conceded_units) AS conceded_units
  FROM concession_raw c
  JOIN shipped_raw s
    ON CAST(c.asin AS TEXT) = CAST(s.asin AS TEXT)
   AND c.mapped_year = s.year
   AND c.mapped_month = s.month
   AND c.mapped_week = s.week
  GROUP BY 1
)
SELECT
  s.brand_name,
  s.shipped_units,
  c.conceded_units,
  (c.conceded_units * 100.0) / NULLIF(s.shipped_units, 0) AS return_rate_pct
FROM s
JOIN c
  ON c.brand_name = s.brand_name
WHERE c.conceded_units > 0
ORDER BY return_rate_pct DESC, c.conceded_units DESC, s.shipped_units DESC;