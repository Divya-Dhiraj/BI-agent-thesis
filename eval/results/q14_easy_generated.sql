SELECT COUNT(DISTINCT CAST(asin AS TEXT)) AS distinct_asins_with_returns
FROM concession_raw
WHERE conceded_units > 0;