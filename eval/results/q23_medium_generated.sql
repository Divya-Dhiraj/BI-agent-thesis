SELECT
  c.defect_category,
  COUNT(*) AS return_count,
  SUM(c.conceded_units) AS conceded_units
FROM concession_raw c
GROUP BY
  c.defect_category
ORDER BY
  return_count DESC;