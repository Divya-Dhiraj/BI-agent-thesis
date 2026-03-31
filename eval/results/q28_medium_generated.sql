WITH defect_rootcause AS (
  SELECT
    c.defect_category,
    c.root_cause,
    SUM(c.conceded_units) AS total_conceded_units,
    SUM(c.ncrc) AS total_ncrc
  FROM concession_raw c
  GROUP BY
    c.defect_category,
    c.root_cause
),
top_defect AS (
  SELECT
    defect_category,
    SUM(total_conceded_units) AS defect_conceded_units,
    SUM(total_ncrc) AS defect_ncrc
  FROM defect_rootcause
  GROUP BY defect_category
  ORDER BY defect_conceded_units DESC
  LIMIT 1
)
SELECT
  td.defect_category,
  td.defect_conceded_units,
  td.defect_ncrc,
  dr.root_cause,
  dr.total_conceded_units AS rootcause_conceded_units,
  dr.total_ncrc AS rootcause_ncrc
FROM top_defect td
JOIN defect_rootcause dr
  ON dr.defect_category = td.defect_category
ORDER BY dr.total_conceded_units DESC, dr.total_ncrc DESC
LIMIT 1;