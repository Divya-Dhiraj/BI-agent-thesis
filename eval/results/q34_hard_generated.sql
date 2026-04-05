SELECT
  c.brand_name,
  SUM(c.ncrc) AS total_ncrc
FROM concession_raw c
GROUP BY
  c.brand_name
ORDER BY
  total_ncrc DESC;