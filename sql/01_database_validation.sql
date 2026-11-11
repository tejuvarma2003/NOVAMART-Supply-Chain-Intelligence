-- Source-synthetic daily panel and additional simulated procurement.
SELECT 'locations' AS table_name, COUNT(*) AS row_count FROM locations UNION ALL
SELECT 'local_skus', COUNT(*) FROM local_skus UNION ALL
SELECT 'daily_operations', COUNT(*) FROM daily_operations UNION ALL
SELECT 'suppliers', COUNT(*) FROM suppliers UNION ALL
SELECT 'sku_supplier_map', COUNT(*) FROM sku_supplier_map UNION ALL
SELECT 'purchase_orders', COUNT(*) FROM purchase_orders UNION ALL
SELECT 'receipts', COUNT(*) FROM receipts;

SELECT MIN(date) AS first_day, MAX(date) AS last_day,
       COUNT(DISTINCT date) AS daily_dates, COUNT(DISTINCT local_sku_id) AS local_skus
FROM daily_operations;

-- This query must return no rows; PRAGMA foreign_key_check is also run by the loader.
SELECT 'po_without_receipt' AS problem, COUNT(*) AS affected
FROM purchase_orders p LEFT JOIN receipts r ON r.po_id=p.po_id
WHERE r.po_id IS NULL HAVING COUNT(*) > 0;
