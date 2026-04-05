SELECT
  CAST(c.asin AS TEXT) AS asin,
  MAX(c.item_name) AS item_name,
  MAX(c.brand_name) AS brand_name,
  MAX(c.manufacturer_name) AS manufacturer_name,
  COUNT(*) AS andon_events,
  SUM(c.conceded_units) AS conceded_units,
  SUM(c.ncrc) AS total_ncrc,
  MIN(c.year * 100 + c.month) AS first_andon_yyyymm,
  MAX(c.year * 100 + c.month) AS last_andon_yyyymm
FROM concession_raw c
WHERE c.is_andon_cord = 'Y'
GROUP BY CAST(c.asin AS TEXT)
ORDER BY total_ncrc DESC, andon_events DESC, conceded_units DESC;