SELECT
  COALESCE(SUM(s.shipped_units), 0) AS shipped_units
FROM shipped_raw s
WHERE (s.brand_name ILIKE '%Samsung%' OR s.item_name ILIKE '%Samsung%');