SELECT
  c.asp_bucket,
  SUM(s.shipped_units) AS shipped_units,
  SUM(s.product_gms) AS product_gms,
  CASE
    WHEN SUM(s.shipped_units) = 0 THEN NULL
    ELSE SUM(s.product_gms) / SUM(s.shipped_units)
  END AS avg_selling_price
FROM shipped_raw s
JOIN concession_raw c
  ON CAST(c.asin AS TEXT) = CAST(s.asin AS TEXT)
 AND c.mapped_year = s.year
 AND c.mapped_month = s.month
 AND c.mapped_week = s.week
GROUP BY
  c.asp_bucket
ORDER BY
  c.asp_bucket;