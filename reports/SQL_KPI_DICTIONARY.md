# Phase 4 SQL KPI dictionary

All base observations in the Kaggle dataset are publisher-generated **synthetic** records. `SOURCE` below means directly supplied in that public file, not observed real-world operations. Procurement and supplier events are additional `SIMULATED` NOVAMART scenarios. `DERIVED` means computed from a named input. No industry benchmark is assumed.

| KPI | Business meaning and exact formula | Tables and lineage | Limits |
| --- | --- | --- | --- |
| Units sold | `SUM(units_sold)`; fulfilled volume | `daily_operations`; SOURCE synthetic | Stock-constrained sales may understate unconstrained demand. |
| Average publisher estimated demand | `AVG(estimated_demand_source)` over selected SKU-days | `daily_operations`; SOURCE synthetic | Not verified customer orders or future forecast ground truth. |
| Latest inventory position | Inventory units on each local SKU's maximum available date; sum across SKU only after selecting latest row | `daily_operations`; SOURCE synthetic + DERIVED latest-date selection | Snapshot timing unknown; excludes inbound POs. |
| Zero-inventory frequency | `SUM(inventory_units=0)/COUNT(*)` over selected SKU-days | `daily_operations`; SOURCE synthetic + DERIVED rate | Zero stock does not prove lost sales or duration within day. |
| Below-50 inventory days | `SUM(inventory_units<50)` | `daily_operations`; SOURCE synthetic + DERIVED count | 50 is a descriptive threshold, not SKU-specific policy. |
| Coverage-days proxy | Latest inventory / mean `units_sold` over preceding 28 calendar days (`SUM/28`) | `daily_operations`; SOURCE synthetic + DERIVED ratio | Undefined if mean sales zero; not safety stock or reorder point. Seven-day management filter is illustrative. |
| Monthly units sold | `SUM(units_sold)` grouped by calendar month | `daily_operations`; SOURCE synthetic + DERIVED month | January 2024 is incomplete; compare complete months carefully. |
| Ordered procurement spend | `SUM(ordered_quantity × procurement_unit_cost)` | `purchase_orders`; SIMULATED + DERIVED | Ordered commitment, not received spend, payment, savings, or audited currency. |
| Average PO quantity | `AVG(ordered_quantity)` per PO | `purchase_orders`; SIMULATED + DERIVED | One simulated SKU line per PO. |
| Expected lead time | `julianday(expected_delivery_date) − julianday(order_date)` per PO; mean across eligible POs | `purchase_orders`; SIMULATED + DERIVED | Scenario promise, not observed supplier quote. |
| Actual lead time | `julianday(actual_delivery_date) − julianday(order_date)` per joined PO/receipt; mean across joined receipts | `purchase_orders`, `receipts`; SIMULATED + DERIVED | One receipt per PO by scenario design. |
| Lead-time variability | Population SD = `sqrt(AVG(actual_days²) − AVG(actual_days)²)` | `purchase_orders`, `receipts`; SIMULATED + DERIVED | Dispersion from simulated outcomes, rounded to two decimals. |
| On-time delivery % | `100 × COUNT(actual_date <= expected_date)/COUNT(eligible joined receipts)` | `purchase_orders`, `receipts`; SIMULATED + DERIVED | Equal date counts on time; all 5,299 records eligible in this scenario. |
| Late delivery % | `100 × COUNT(actual_date > expected_date)/COUNT(eligible joined receipts)` | Same; SIMULATED + DERIVED | Complements on-time percentage before rounding. |
| Average delivery delay | Across all receipts, `AVG(MAX(0, actual_date − expected_date))`; separately report mean positive delay among late receipts | Same; SIMULATED + DERIVED | Early deliveries contribute zero to all-receipts measure. |
| Receipt fill % | `100 × SUM(received_quantity)/SUM(ordered_quantity)` at chosen supplier or total grain | Same; SIMULATED + DERIVED | Unit-weighted quantity fill, not share of fully received orders. |

Phase 4 intentionally excludes forecast accuracy, safety stock, EOQ, optimized reorder points, replenishment quantities, and final supplier scores.
