WITH sales_by_brand AS (
  SELECT
    s.brand_name,
    SUM(s.product_gms) AS total_gms,
    SUM(s.shipped_cogs) AS total_shipped_cogs
  FROM shipped_raw s
  GROUP BY 1
),
returns_by_brand AS (
  SELECT
    c.brand_name,
    SUM(c.ncrc) AS total_ncrc
  FROM concession_raw c
  GROUP BY 1
),
net_margin_by_brand AS (
  SELECT
    COALESCE(sb.brand_name, rb.brand_name) AS brand_name,
    COALESCE(sb.total_gms, 0) AS total_gms,
    COALESCE(sb.total_shipped_cogs, 0) AS total_shipped_cogs,
    COALESCE(rb.total_ncrc, 0) AS total_ncrc,
    COALESCE(sb.total_gms, 0) - COALESCE(sb.total_shipped_cogs, 0) - COALESCE(rb.total_ncrc, 0) AS net_margin
  FROM sales_by_brand sb
  FULL OUTER JOIN returns_by_brand rb
    ON sb.brand_name = rb.brand_name
)
SELECT
  brand_name,
  total_gms,
  total_shipped_cogs,
  total_ncrc,
  net_margin
FROM net_margin_by_brand
ORDER BY net_margin DESC
LIMIT 20;