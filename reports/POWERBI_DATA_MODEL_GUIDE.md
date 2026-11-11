# Phase 9 Power BI data-model preparation (no dashboard built)

Import the existing CSVs or SQLite outputs. Keep an explicit source label on every view. Prefer a star-style reporting model with one-direction dimension-to-fact filters and unique keys. Avoid activating ambiguous paths through both location and local SKU relationships; use `local_skus` as the SKU-to-location bridge and document any direct location relationship.

| Table/file | Grain and key | Role / links | Provenance |
| --- | --- | --- | --- |
| `locations.csv` | 1 per `location_id` | Location dimension; 1→many `local_skus` | SOURCE store/region + DERIVED name |
| `local_skus.csv` | 1 per `local_sku_id` | SKU dimension; many→1 location; 1→many daily/forecast/PO facts | SOURCE IDs/category + DERIVED local key |
| `daily_operations.csv` | 1 per date × local SKU | Historical fact, many→1 local SKU and date dimension | Published SOURCE synthetic observations + DERIVED calendar |
| `suppliers.csv` | 1 per `supplier_id` | Supplier dimension, 1→many PO and mapping | SIMULATED |
| `sku_supplier_map.csv` | 1 per local SKU × supplier | Sourcing bridge, many→1 SKU and supplier | SIMULATED; one primary per SKU in this scenario |
| `purchase_orders.csv` | 1 per `po_id` | Procurement fact, many→1 supplier/SKU; order date to date dimension | SIMULATED; ordered commitment, not paid spend |
| `receipts.csv` | 1 per `receipt_id`, unique `po_id` | 1→1 PO; actual receipt date can use an inactive date relation | SIMULATED |
| `demand_forecast_14d.csv` | 1 per future date × local SKU | Forecast fact, many→1 SKU/date | FORECAST from published synthetic source |
| `replenishment_recommendations.csv` | 1 per snapshot date × local SKU (current export one date) | Planning fact, many→1 SKU; assumed/simulated fields labeled | SOURCE snapshot + FORECAST + DERIVED + SIMULATED/ASSUMED policy |
| `abc_inventory_classification.csv` | 1 per local SKU for 2023 | 1→1 SKU analytical attribute or separate bridge; do not duplicate daily rows | SOURCE-based DERIVED sales-value proxy |
| `supplier_scorecard.csv` | 1 per simulated supplier | 1→1 supplier scenario analytical attribute | SIMULATED outcomes + DERIVED scores with ASSUMED weights |
| `supply_chain_priority_matrix.csv` | 1 per local SKU at 2024-01-30 snapshot | One current combined analytical fact; use directly for management exceptions, not summed alongside recommendation fact | Mixed provenance explicitly documented |

Create a date dimension spanning source history, receipt dates, and future forecasts. Use an active date relationship appropriate to each fact; PO order date and receipt actual date should not be conflated. Use `local_sku_id`, never source `original_product_id` alone, as the cross-table SKU key. Do not sum `supplier_scorecard` across SKU joins or multiply PO commitment by joined receipts. Measures should distinguish historical sold units, forecast units, simulated ordered commitment, and scenario recommended units. Keep supplier results visibly labeled **SIMULATED NOVAMART PROCUREMENT SCENARIO**. Validate row counts and totals after import against Phase 4–8 manifests before designing visuals.
