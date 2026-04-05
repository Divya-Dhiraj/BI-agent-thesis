SELECT
  COUNT(DISTINCT CAST(asin AS TEXT)) AS distinct_asins_with_returns
FROM concession_raw
WHERE COALESCE(conceded_units, 0) > 0;