WITH shipped_by_year AS (
  SELECT
    s.year,
    SUM(s.shipped_units) AS shipped_units
  FROM shipped_raw s
  GROUP BY s.year
),
conceded_by_mapped_year AS (
  SELECT
    c.mapped_year AS year,
    SUM(c.conceded_units) AS conceded_units
  FROM concession_raw c
  GROUP BY c.mapped_year
)
SELECT
  sy.year,
  (COALESCE(cy.conceded_units, 0) * 100.0) / NULLIF(sy.shipped_units, 0) AS return_rate_pct
FROM shipped_by_year sy
LEFT JOIN conceded_by_mapped_year cy
  ON cy.year = sy.year
ORDER BY return_rate_pct DESC NULLS LAST
LIMIT 1;