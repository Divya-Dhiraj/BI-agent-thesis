SELECT
  c.recovery_channel,
  SUM(c.conceded_units) AS conceded_units,
  COUNT(*) AS concession_records,
  (SUM(c.conceded_units) * 100.0) / NULLIF(SUM(SUM(c.conceded_units)) OVER (), 0) AS pct_of_total_units
FROM concession_raw c
GROUP BY
  c.recovery_channel
ORDER BY
  conceded_units DESC;