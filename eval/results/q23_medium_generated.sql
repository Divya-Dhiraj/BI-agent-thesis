SELECT
  defect_category,
  COUNT(*) AS return_records,
  SUM(conceded_units) AS conceded_units
FROM concession_raw
GROUP BY defect_category
ORDER BY conceded_units DESC, return_records DESC;