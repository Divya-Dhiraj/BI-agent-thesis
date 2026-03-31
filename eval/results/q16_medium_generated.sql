SELECT
  (SUM(c.conceded_units) * 100.0) / NULLIF(SUM(s.shipped_units), 0) AS cir_pct_2025
FROM shipped_raw s
LEFT JOIN concession_raw c
  ON CAST(c.asin AS TEXT) = CAST(s.asin AS TEXT)
 AND c.mapped_year = s.year
 AND c.mapped_month = s.month
 AND c.mapped_week = s.week
WHERE s.year = 2025;