-- All spend below is SIMULATED ordered commitment: ordered quantity * PO cost.
SELECT COUNT(*) AS purchase_orders, ROUND(SUM(ordered_quantity*procurement_unit_cost),2) AS ordered_spend,
       ROUND(AVG(ordered_quantity),2) AS avg_ordered_quantity
FROM purchase_orders;

SELECT p.supplier_id, s.supplier_name, COUNT(*) AS purchase_orders,
       ROUND(SUM(p.ordered_quantity*p.procurement_unit_cost),2) AS ordered_spend
FROM purchase_orders p JOIN suppliers s USING(supplier_id)
GROUP BY p.supplier_id, s.supplier_name ORDER BY ordered_spend DESC;

SELECT location_id, COUNT(*) AS purchase_orders,
       ROUND(SUM(ordered_quantity*procurement_unit_cost),2) AS ordered_spend
FROM purchase_orders GROUP BY location_id ORDER BY ordered_spend DESC;

SELECT s.category, COUNT(*) AS purchase_orders,
       ROUND(SUM(p.ordered_quantity*p.procurement_unit_cost),2) AS ordered_spend
FROM purchase_orders p JOIN local_skus s USING(local_sku_id)
GROUP BY s.category ORDER BY ordered_spend DESC;

SELECT r.delivery_status, COUNT(*) AS receipts, SUM(r.received_quantity) AS received_units
FROM receipts r GROUP BY r.delivery_status;

SELECT substr(order_date,1,7) AS month, COUNT(*) AS purchase_orders,
       ROUND(SUM(ordered_quantity*procurement_unit_cost),2) AS ordered_spend
FROM purchase_orders GROUP BY substr(order_date,1,7) ORDER BY month;
