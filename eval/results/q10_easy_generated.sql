SELECT
  COUNT(DISTINCT CAST(s.asin AS TEXT)) AS distinct_iphone_asins_shipped
FROM shipped_raw s
WHERE s.item_name ILIKE '%iPhone%';