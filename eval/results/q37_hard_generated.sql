SELECT
  c.return_window,
  SUM(c.conceded_units) AS conceded_units,
  SUM(c.ncrc) AS total_ncrc
FROM concession_raw c
WHERE c.marketplace_id = 4
GROUP BY
  c.return_window
ORDER BY
  conceded_units DESC,
  total_ncrc DESC;