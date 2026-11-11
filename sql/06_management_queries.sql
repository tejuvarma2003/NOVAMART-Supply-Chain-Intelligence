-- Descriptive exception as of latest source date; no proposed order quantity.
WITH anchor AS (SELECT MAX(date) AS max_date FROM daily_operations), recent AS (
 SELECT d.local_sku_id, SUM(d.units_sold)/28.0 AS avg_daily_sales_28d
 FROM daily_operations d CROSS JOIN anchor a
 WHERE d.date>date(a.max_date,'-28 days') GROUP BY d.local_sku_id
)
SELECT d.local_sku_id, d.location_id, d.inventory_units,
       ROUND(r.avg_daily_sales_28d,2) AS avg_daily_sales_28d,
       ROUND(d.inventory_units/NULLIF(r.avg_daily_sales_28d,0),2) AS coverage_days_proxy,
       'SOURCE_SYNTHETIC_PLUS_DERIVED' AS data_origin
FROM daily_operations d JOIN recent r USING(local_sku_id)
WHERE d.date=(SELECT max_date FROM anchor) AND r.avg_daily_sales_28d>0
  AND d.inventory_units/r.avg_daily_sales_28d<7
ORDER BY coverage_days_proxy, d.local_sku_id;

-- Historical zero stock is a descriptive flag, not proof of lost sales.
SELECT local_sku_id, location_id, COUNT(*) AS zero_inventory_days
FROM daily_operations WHERE inventory_units=0
GROUP BY local_sku_id, location_id ORDER BY zero_inventory_days DESC LIMIT 15;

-- Simulated supplier/location late-delivery combinations.
SELECT p.supplier_id, p.location_id, COUNT(*) AS receipts,
       SUM(CASE WHEN r.actual_delivery_date>p.expected_delivery_date THEN 1 ELSE 0 END) AS late_receipts,
       ROUND(AVG(CASE WHEN r.actual_delivery_date>p.expected_delivery_date
                      THEN julianday(r.actual_delivery_date)-julianday(p.expected_delivery_date) END),2) AS avg_delay_late_only_days
FROM purchase_orders p JOIN receipts r USING(po_id)
GROUP BY p.supplier_id, p.location_id ORDER BY late_receipts DESC, p.supplier_id, p.location_id;
