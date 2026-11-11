-- Latest recorded snapshot per local SKU. This is historical as of the source end date.
WITH latest AS (
 SELECT d.*, ROW_NUMBER() OVER(PARTITION BY local_sku_id ORDER BY date DESC) AS rn
 FROM daily_operations d
)
SELECT l.date, l.local_sku_id, l.location_id, s.category, l.inventory_units
FROM latest l JOIN local_skus s USING(local_sku_id)
WHERE rn=1 ORDER BY inventory_units, local_sku_id;

WITH latest AS (
 SELECT d.*, ROW_NUMBER() OVER(PARTITION BY local_sku_id ORDER BY date DESC) AS rn
 FROM daily_operations d
)
SELECT location_id, SUM(inventory_units) AS latest_inventory_units
FROM latest WHERE rn=1 GROUP BY location_id ORDER BY latest_inventory_units DESC;

WITH latest AS (
 SELECT d.*, ROW_NUMBER() OVER(PARTITION BY local_sku_id ORDER BY date DESC) AS rn FROM daily_operations d
)
SELECT s.category, SUM(l.inventory_units) AS latest_inventory_units
FROM latest l JOIN local_skus s USING(local_sku_id) WHERE rn=1
GROUP BY s.category ORDER BY latest_inventory_units DESC;

SELECT local_sku_id, SUM(CASE WHEN inventory_units=0 THEN 1 ELSE 0 END) AS zero_inventory_days,
       SUM(CASE WHEN inventory_units<50 THEN 1 ELSE 0 END) AS below_50_days,
       COUNT(*) AS observed_days
FROM daily_operations GROUP BY local_sku_id
HAVING zero_inventory_days>0 OR below_50_days>0
ORDER BY zero_inventory_days DESC, below_50_days DESC;

-- Descriptive 28-day coverage proxy; a threshold is not an optimized reorder point.
WITH anchor AS (SELECT MAX(date) AS max_date FROM daily_operations),
recent AS (
 SELECT d.local_sku_id, SUM(d.units_sold)/28.0 AS mean_daily_sales
 FROM daily_operations d CROSS JOIN anchor a
 WHERE d.date>date(a.max_date,'-28 days') GROUP BY d.local_sku_id
), current_stock AS (
 SELECT d.local_sku_id, d.location_id, d.inventory_units FROM daily_operations d
 WHERE d.date=(SELECT max_date FROM anchor)
)
SELECT c.local_sku_id, c.location_id, c.inventory_units, ROUND(r.mean_daily_sales,2) AS mean_daily_sales_28d,
       ROUND(c.inventory_units/NULLIF(r.mean_daily_sales,0),2) AS coverage_days_proxy
FROM current_stock c JOIN recent r USING(local_sku_id)
ORDER BY coverage_days_proxy DESC;

SELECT substr(date,1,7) AS month, ROUND(AVG(inventory_units),2) AS avg_snapshot_units
FROM daily_operations GROUP BY substr(date,1,7) ORDER BY month;
