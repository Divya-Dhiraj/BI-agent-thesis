WITH sales AS (
  SELECT
    s.fulfillment_channel,
    SUM(s.shipped_units) AS shipped_units,
    SUM(s.product_gms)   AS total_sales_gms
  FROM shipped_raw s
  GROUP BY 1
),
returns_mapped AS (
  SELECT
    s.fulfillment_channel,
    SUM(c.conceded_units) AS conceded_units
  FROM concession_raw c
  JOIN shipped_raw s
    ON CAST(c.asin AS TEXT) = CAST(s.asin AS TEXT)
   AND c.mapped_year = s.year
   AND c.mapped_month = s.month
   AND c.mapped_week = s.week
  GROUP BY 1
)
SELECT
  sa.fulfillment_channel,
  sa.total_sales_gms,
  sa.shipped_units,
  COALESCE(rm.conceded_units, 0) AS conceded_units,
  (COALESCE(rm.conceded_units, 0) * 100.0) / NULLIF(sa.shipped_units, 0) AS return_rate_pct
FROM sales sa
LEFT JOIN returns_mapped rm
  ON rm.fulfillment_channel = sa.fulfillment_channel
ORDER BY sa.total_sales_gms DESC;