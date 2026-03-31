WITH shipped AS (
  SELECT
    s.year,
    s.month,
    s.brand_name,
    SUM(s.product_gms)  AS product_gms,
    SUM(s.shipped_cogs) AS shipped_cogs,
    SUM(s.shipped_units) AS shipped_units
  FROM shipped_raw s
  WHERE s.brand_name ILIKE ANY (ARRAY['%Apple%', '%Samsung%'])
  GROUP BY 1,2,3
),
concessions AS (
  SELECT
    c.mapped_year AS year,
    c.mapped_month AS month,
    c.brand_name,
    SUM(c.ncrc) AS ncrc,
    SUM(c.conceded_units) AS conceded_units
  FROM concession_raw c
  WHERE c.brand_name ILIKE ANY (ARRAY['%Apple%', '%Samsung%'])
  GROUP BY 1,2,3
)
SELECT
  COALESCE(s.year, c.year)   AS year,
  COALESCE(s.month, c.month) AS month,
  COALESCE(s.brand_name, c.brand_name) AS brand_name,
  COALESCE(s.product_gms, 0)  AS product_gms,
  COALESCE(s.shipped_cogs, 0) AS shipped_cogs,
  COALESCE(c.ncrc, 0)         AS ncrc,
  (COALESCE(s.product_gms, 0) - COALESCE(s.shipped_cogs, 0) - COALESCE(c.ncrc, 0)) AS net_margin
FROM shipped s
FULL OUTER JOIN concessions c
  ON c.year = s.year
 AND c.month = s.month
 AND c.brand_name = s.brand_name
ORDER BY year, month, brand_name;