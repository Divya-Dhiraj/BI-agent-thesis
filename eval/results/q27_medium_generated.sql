WITH sales_by_year AS (
  SELECT
    s.year AS sales_year,
    SUM(s.shipped_units) AS shipped_units
  FROM shipped_raw s
  GROUP BY s.year
),
returns_by_sales_year AS (
  SELECT
    c.mapped_year AS sales_year,
    SUM(c.conceded_units) AS conceded_units
  FROM concession_raw c
  GROUP BY c.mapped_year
)
SELECT
  sy.sales_year AS year,
  COALESCE(ry.conceded_units, 0) AS conceded_units,
  sy.shipped_units,
  (COALESCE(ry.conceded_units, 0) * 100.0) / NULLIF(sy.shipped_units, 0) AS return_rate_pct
FROM sales_by_year sy
LEFT JOIN returns_by_sales_year ry
  ON ry.sales_year = sy.sales_year
ORDER BY return_rate_pct DESC NULLS LAST
LIMIT 1;