SELECT
  c.year AS return_year,
  c.month AS return_month,
  SUM(c.conceded_units) AS conceded_units,
  SUM(c.ncrc) AS ncrc
FROM concession_raw c
GROUP BY
  c.year,
  c.month
ORDER BY
  return_year,
  return_month;