SELECT DISTINCT
  CAST(asin AS TEXT) AS asin,
  item_name
FROM shipped_raw
WHERE asin IS NOT NULL;