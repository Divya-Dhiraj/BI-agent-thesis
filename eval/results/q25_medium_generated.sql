SELECT
  s.year,
  s.month,
  SUM(s.shipped_units) AS shipped_units,
  COALESCE(SUM(c.conceded_units), 0) AS conceded_units,
  (COALESCE(SUM(c.conceded_units), 0) * 100.0) / NULLIF(SUM(s.shipped_units), 0) AS return_rate_pct
FROM shipped_raw s
LEFT JOIN concession_raw c
  ON CAST(c.asin AS TEXT) = CAST(s.asin AS TEXT)
 AND c.mapped_year = s.year
 AND c.mapped_month = s.month
 AND c.mapped_week = s.week
 AND c.item_name ILIKE '%iPhone%'
WHERE s.item_name ILIKE '%iPhone%'
GROUP BY
  s.year,
  s.month
ORDER BY
  s.year,
  s.month;