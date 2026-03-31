WITH s AS (
  SELECT
    brand_name,
    SUM(shipped_units) AS shipped_units,
    SUM(product_gms)   AS product_gms
  FROM shipped_raw
  GROUP BY 1
),
c AS (
  SELECT
    brand_name,
    SUM(conceded_units) AS conceded_units
  FROM concession_raw
  GROUP BY 1
)
SELECT
  s.brand_name,
  s.shipped_units,
  s.product_gms,
  c.conceded_units,
  (c.conceded_units * 100.0) / NULLIF(s.shipped_units, 0) AS return_rate_pct
FROM s
JOIN c
  ON c.brand_name = s.brand_name
WHERE c.conceded_units > 0
ORDER BY return_rate_pct DESC, c.conceded_units DESC;