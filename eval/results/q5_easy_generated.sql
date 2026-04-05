SELECT
  SUM(s.shipped_units) AS shipped_units_samsung
FROM shipped_raw s
WHERE (s.brand_name ILIKE '%Samsung%' OR s.item_name ILIKE '%Samsung%');