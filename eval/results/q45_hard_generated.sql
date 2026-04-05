WITH s AS (
  SELECT
    s.year,
    s.month,
    s.brand_name,
    SUM(s.product_gms)  AS product_gms,
    SUM(s.shipped_cogs) AS shipped_cogs,
    SUM(s.shipped_units) AS shipped_units
  FROM shipped_raw s
  WHERE s.brand_name IN ('Apple', 'Samsung')
  GROUP BY 1, 2, 3
),
c AS (
  SELECT
    c.mapped_year AS year,
    c.mapped_month AS month,
    c.brand_name,
    SUM(c.ncrc) AS ncrc,
    SUM(c.conceded_units) AS conceded_units
  FROM concession_raw c
  WHERE c.brand_name IN ('Apple', 'Samsung')
  GROUP BY 1, 2, 3
)
SELECT
  s.year,
  s.month,
  s.brand_name,
  s.product_gms,
  s.shipped_cogs,
  COALESCE(c.ncrc, 0) AS ncrc,
  (s.product_gms - s.shipped_cogs - COALESCE(c.ncrc, 0)) AS net_margin,
  s.shipped_units,
  COALESCE(c.conceded_units, 0) AS conceded_units,
  (COALESCE(c.conceded_units, 0) * 100.0) / NULLIF(s.shipped_units, 0) AS return_rate_pct
FROM s
LEFT JOIN c
  ON c.brand_name = s.brand_name
 AND c.year = s.year
 AND c.month = s.month
ORDER BY s.year, s.month, s.brand_name;