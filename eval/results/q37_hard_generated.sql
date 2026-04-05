SELECT
  c.return_window,
  SUM(c.conceded_units) AS conceded_units,
  SUM(c.ncrc) AS total_ncrc
FROM concession_raw c
GROUP BY
  c.return_window
ORDER BY
  SUM(c.ncrc) DESC,
  SUM(c.conceded_units) DESC;