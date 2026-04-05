SELECT DISTINCT defect_category
FROM concession_raw
WHERE defect_category IS NOT NULL
  AND TRIM(defect_category) <> ''
ORDER BY defect_category;