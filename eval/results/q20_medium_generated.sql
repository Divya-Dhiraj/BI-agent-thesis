SELECT
  fulfillment_channel,
  SUM(shipped_cogs) AS total_shipped_cogs
FROM shipped_raw
GROUP BY fulfillment_channel
ORDER BY total_shipped_cogs DESC;