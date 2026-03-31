SELECT
  c.is_hrr_asin,
  SUM(c.conceded_units) AS conceded_units,
  SUM(c.ncrc) AS total_ncrc,
  COUNT(*) AS concession_records,
  COUNT(DISTINCT c.asin) AS distinct_asins
FROM concession_raw c
GROUP BY
  c.is_hrr_asin
ORDER BY
  total_ncrc DESC;