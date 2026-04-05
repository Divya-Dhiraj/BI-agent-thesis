WITH s AS (
    SELECT
        fulfillment_channel,
        year,
        month,
        week,
        SUM(shipped_units) AS shipped_units,
        SUM(product_gms)  AS product_gms
    FROM shipped_raw
    GROUP BY 1,2,3,4
),
c AS (
    SELECT
        CAST(asin AS TEXT) AS asin,
        mapped_year AS year,
        mapped_month AS month,
        mapped_week AS week,
        SUM(conceded_units) AS conceded_units
    FROM concession_raw
    GROUP BY 1,2,3,4
),
s_by_fc AS (
    SELECT
        fulfillment_channel,
        SUM(shipped_units) AS shipped_units,
        SUM(product_gms)  AS total_sales
    FROM shipped_raw
    GROUP BY 1
),
c_by_fc AS (
    SELECT
        s.fulfillment_channel,
        SUM(c.conceded_units) AS conceded_units
    FROM concession_raw c
    JOIN shipped_raw s
      ON CAST(c.asin AS TEXT) = CAST(s.asin AS TEXT)
     AND c.mapped_year  = s.year
     AND c.mapped_month = s.month
     AND c.mapped_week  = s.week
    GROUP BY 1
)
SELECT
    sfc.fulfillment_channel,
    sfc.total_sales,
    sfc.shipped_units,
    COALESCE(cfc.conceded_units, 0) AS conceded_units,
    (COALESCE(cfc.conceded_units, 0) * 100.0) / NULLIF(sfc.shipped_units, 0) AS return_rate_pct
FROM s_by_fc sfc
LEFT JOIN c_by_fc cfc
  ON cfc.fulfillment_channel = sfc.fulfillment_channel
ORDER BY sfc.total_sales DESC;