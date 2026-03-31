WITH s AS (
  SELECT
    brand_name,
    SUM(product_gms) AS product_gms,
    SUM(shipped_cogs) AS shipped_cogs,
    SUM(shipped_units) AS shipped_units
  FROM shipped_raw
  GROUP BY 1
),
c AS (
  SELECT
    brand_name,
    SUM(ncrc) AS ncrc,
    SUM(conceded_units) AS conceded_units
  FROM concession_raw
  GROUP BY 1
)
SELECT
  s.brand_name,
  (s.product_gms - s.shipped_cogs - COALESCE(c.ncrc, 0)) AS net_margin,
  s.product_gms,
  s.shipped_cogs,
  COALESCE(c.ncrc, 0) AS ncrc,
  s.shipped_units,
  COALESCE(c.conceded_units, 0) AS conceded_units,
  (COALESCE(c.conceded_units, 0) * 100.0) / NULLIF(s.shipped_units, 0) AS return_rate_pct
FROM s
LEFT JOIN c
  ON c.brand_name = s.brand_name
ORDER BY net_margin DESC
LIMIT 20;