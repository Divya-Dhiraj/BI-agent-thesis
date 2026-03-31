SELECT
  c.root_cause,
  c.defect_category,
  SUM(c.conceded_units) AS conceded_units,
  SUM(c.ncrc) AS total_ncrc,
  COUNT(*) AS concession_events
FROM concession_raw c
WHERE c.marketplace_id = 4
GROUP BY
  c.root_cause,
  c.defect_category
ORDER BY
  total_ncrc DESC NULLS LAST,
  conceded_units DESC NULLS LAST
LIMIT 20;