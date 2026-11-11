-- One receipt per PO. All results are within the SIMULATED procurement scenario.
WITH events AS (
 SELECT p.supplier_id, p.po_id, p.ordered_quantity, r.received_quantity,
        p.ordered_quantity*p.procurement_unit_cost AS ordered_spend,
        julianday(p.expected_delivery_date)-julianday(p.order_date) AS expected_days,
        julianday(r.actual_delivery_date)-julianday(p.order_date) AS actual_days,
        julianday(r.actual_delivery_date)-julianday(p.expected_delivery_date) AS delay_days
 FROM purchase_orders p JOIN receipts r ON r.po_id=p.po_id
), summary AS (
 SELECT supplier_id, COUNT(*) AS purchase_orders, SUM(ordered_spend) AS ordered_spend,
        AVG(expected_days) AS avg_expected_lead_days, AVG(actual_days) AS avg_actual_lead_days,
        AVG(actual_days*actual_days)-AVG(actual_days)*AVG(actual_days) AS lead_variance,
        SUM(CASE WHEN delay_days<=0 THEN 1 ELSE 0 END) AS on_time_receipts,
        SUM(CASE WHEN delay_days>0 THEN 1 ELSE 0 END) AS late_receipts,
        AVG(CASE WHEN delay_days>0 THEN delay_days ELSE 0 END) AS avg_positive_delay_all_receipts,
        AVG(CASE WHEN delay_days>0 THEN delay_days END) AS avg_delay_late_only,
        SUM(ordered_quantity) AS ordered_units, SUM(received_quantity) AS received_units
 FROM events GROUP BY supplier_id
)
SELECT s.supplier_id, s.supplier_name, q.purchase_orders, ROUND(q.ordered_spend,2) AS ordered_spend,
       ROUND(q.avg_expected_lead_days,2) AS avg_expected_lead_days,
       ROUND(q.avg_actual_lead_days,2) AS avg_actual_lead_days,
       ROUND(sqrt(MAX(0,q.lead_variance)),2) AS actual_lead_sd_days,
       q.on_time_receipts, q.late_receipts,
       ROUND(100.0*q.on_time_receipts/q.purchase_orders,2) AS on_time_pct,
       ROUND(100.0*q.late_receipts/q.purchase_orders,2) AS late_pct,
       ROUND(q.avg_positive_delay_all_receipts,2) AS avg_positive_delay_all_receipts_days,
       ROUND(q.avg_delay_late_only,2) AS avg_delay_late_only_days,
       q.ordered_units, q.received_units,
       ROUND(100.0*q.received_units/q.ordered_units,2) AS receipt_fill_pct,
       'SIMULATED' AS data_origin
FROM summary q JOIN suppliers s USING(supplier_id)
ORDER BY on_time_pct ASC, s.supplier_id;
