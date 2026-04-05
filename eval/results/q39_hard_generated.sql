SELECT
  c.is_hrr_asin,
  SUM(c.conceded_units) AS conceded_units,
  SUM(c.ncrc) AS total_ncrc,
  SUM(c.gcv) AS total_gcv,
  SUM(c.ncv) AS total_ncv,
  COUNT(*) AS concession_rows
FROM concession_raw c
GROUP BY
  c.is_hrr_asin
ORDER BY
  total_ncrc DESC;