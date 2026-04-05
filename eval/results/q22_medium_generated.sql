SELECT
  c.root_cause,
  c.defect_category,
  SUM(c.conceded_units) AS conceded_units,
  SUM(c.ncrc) AS total_ncrc,
  COUNT(*) AS concession_records
FROM concession_raw c
WHERE c.root_cause IS NOT NULL
GROUP BY
  c.root_cause,
  c.defect_category
ORDER BY
  SUM(c.ncrc) DESC,
  SUM(c.conceded_units) DESC
LIMIT 20;