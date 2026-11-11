-- Observed fulfilled units, not verified unconstrained demand.
SELECT d.local_sku_id, s.category, SUM(d.units_sold) AS units_sold
FROM daily_operations d JOIN local_skus s USING(local_sku_id)
GROUP BY d.local_sku_id, s.category ORDER BY units_sold DESC LIMIT 10;

SELECT s.category, SUM(d.units_sold) AS units_sold,
       ROUND(AVG(d.estimated_demand_source),2) AS avg_publisher_estimate
FROM daily_operations d JOIN local_skus s USING(local_sku_id)
GROUP BY s.category ORDER BY units_sold DESC;

SELECT location_id, SUM(units_sold) AS units_sold FROM daily_operations
GROUP BY location_id ORDER BY units_sold DESC;

SELECT substr(date,1,7) AS month, SUM(units_sold) AS units_sold
FROM daily_operations GROUP BY substr(date,1,7) ORDER BY month;

-- Volatility is relative to average observed sales, not a demand forecast.
WITH moments AS (
 SELECT local_sku_id, AVG(units_sold) AS mean_units,
        AVG(units_sold * 1.0 * units_sold) - AVG(units_sold) * AVG(units_sold) AS variance
 FROM daily_operations GROUP BY local_sku_id
)
SELECT local_sku_id, ROUND(mean_units,2) AS mean_daily_units,
       ROUND(sqrt(MAX(0,variance)),2) AS population_sd,
       ROUND(sqrt(MAX(0,variance))/NULLIF(mean_units,0),3) AS coefficient_of_variation
FROM moments ORDER BY coefficient_of_variation DESC LIMIT 10;

-- Association only; promotions were not randomized and are not causal evidence.
SELECT promotion_flag, COUNT(*) AS sku_days, ROUND(AVG(units_sold),2) AS avg_units_sold
FROM daily_operations GROUP BY promotion_flag ORDER BY promotion_flag;

SELECT seasonality_label, COUNT(*) AS sku_days, ROUND(AVG(units_sold),2) AS avg_units_sold
FROM daily_operations GROUP BY seasonality_label ORDER BY seasonality_label;
