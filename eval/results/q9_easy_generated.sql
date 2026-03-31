SELECT
  SUM(conceded_units) AS returned_units_2024
FROM concession_raw
WHERE year = 2024;