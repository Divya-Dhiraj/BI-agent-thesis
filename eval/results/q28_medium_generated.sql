WITH defect_totals AS (
    SELECT
        c.defect_category,
        SUM(c.conceded_units) AS total_conceded_units
    FROM concession_raw c
    GROUP BY 1
),
top_defect AS (
    SELECT
        defect_category,
        total_conceded_units
    FROM defect_totals
    ORDER BY total_conceded_units DESC NULLS LAST
    LIMIT 1
)
SELECT
    c.defect_category,
    c.root_cause,
    SUM(c.conceded_units) AS conceded_units,
    SUM(c.ncrc) AS total_ncrc
FROM concession_raw c
JOIN top_defect td
  ON td.defect_category = c.defect_category
GROUP BY
    c.defect_category,
    c.root_cause
ORDER BY
    conceded_units DESC NULLS LAST
LIMIT 1;