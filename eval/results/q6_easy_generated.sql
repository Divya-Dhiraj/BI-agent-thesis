SELECT
  SUM(c.conceded_units) AS total_conceded_units
FROM concession_raw c
WHERE c.brand_name ILIKE '%Apple%';