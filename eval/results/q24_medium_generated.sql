SELECT
  c.recovery_channel,
  SUM(c.conceded_units) AS conceded_units
FROM concession_raw c
GROUP BY c.recovery_channel
ORDER BY conceded_units DESC;