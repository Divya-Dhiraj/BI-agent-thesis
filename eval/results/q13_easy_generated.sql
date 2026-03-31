SELECT DISTINCT defect_category
FROM concession_raw
WHERE defect_category IS NOT NULL
ORDER BY defect_category;