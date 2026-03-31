SELECT
  CAST(c.asin AS TEXT) AS asin,
  c.item_name,
  MAX(c.is_andon_cord) AS is_andon_cord,
  SUM(c.conceded_units) AS conceded_units,
  SUM(c.ncrc) AS total_ncrc,
  COUNT(*) AS concession_records,
  MIN(c.year * 100 + c.month) AS first_concession_yyyymm,
  MAX(c.year * 100 + c.month) AS last_concession_yyyymm
FROM concession_raw c
WHERE c.is_andon_cord = 'Y'
  AND c.item_name ILIKE '%andon cord%'
GROUP BY
  CAST(c.asin AS TEXT),
  c.item_name
ORDER BY
  total_ncrc DESC;