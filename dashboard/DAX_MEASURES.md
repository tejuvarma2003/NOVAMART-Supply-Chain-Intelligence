# DAX measure library

Create these as **New measure** in a dedicated measure table (Home → Enter data, one dummy row, name it `_Measures`, then hide its dummy column), or in the relevant fact table. Paste **one definition at a time**. Table names match CSV basenames. Format units as whole numbers except forecast and policy parameters as two decimals; percentages as percentages. Blank means undefined, not zero. Do not sum per-SKU policy thresholds as if they were operational stock.

## Demand and holdout

```DAX
Total Units Sold = SUM(daily_operations[units_sold])

Average Daily Units Sold =
DIVIDE([Total Units Sold], DISTINCTCOUNT(daily_operations[date]))

14-Day Forecast Units = SUM(demand_forecast_14d[predicted_units])

Forecast MAE =
CALCULATE(
    AVERAGEX(forecast_holdout_predictions,
        ABS(forecast_holdout_predictions[actual] - forecast_holdout_predictions[prediction])),
    forecast_holdout_predictions[split] = "test"
)

Forecast WAPE =
CALCULATE(
    DIVIDE(
        SUMX(forecast_holdout_predictions,
            ABS(forecast_holdout_predictions[actual] - forecast_holdout_predictions[prediction])),
        SUM(forecast_holdout_predictions[actual])
    ),
    forecast_holdout_predictions[split] = "test"
)

Baseline 28-Day WAPE =
CALCULATE(
    DIVIDE(
        SUMX(forecast_holdout_predictions,
            ABS(forecast_holdout_predictions[actual] - forecast_holdout_predictions[mean_28])),
        SUM(forecast_holdout_predictions[actual])
    ),
    forecast_holdout_predictions[split] = "test"
)
```

The test metrics are pooled over eligible test forecast rows, not an average of per-SKU percentages; valid slice denominators may change. Display Forecast WAPE and baseline as percentages. Forecast value is expected units, not physical order units. Use `sku_demand_profile[cv_daily_units]` as a **per-SKU column** in a table; do not sum CVs.

## Inventory, ABC, action priority

```DAX
Latest Inventory Units = SUM(replenishment_recommendations[current_inventory])

Reorder Point (selected SKU) =
IF(HASONEVALUE(local_skus[local_sku_id]),
    MAX(replenishment_recommendations[reorder_point]))

Safety Stock (selected SKU) =
IF(HASONEVALUE(local_skus[local_sku_id]),
    MAX(replenishment_recommendations[safety_stock]))

Average Reorder Point = AVERAGE(replenishment_recommendations[reorder_point])

Average Safety Stock = AVERAGE(replenishment_recommendations[safety_stock])

SKUs Requiring Reorder =
CALCULATE(COUNTROWS(replenishment_recommendations),
    replenishment_recommendations[inventory_status] = "REORDER REQUIRED")

Stockout SKUs =
CALCULATE(COUNTROWS(replenishment_recommendations),
    replenishment_recommendations[current_inventory] = 0)

Low Stock SKUs =
CALCULATE(COUNTROWS(replenishment_recommendations),
    replenishment_recommendations[inventory_status] = "LOW STOCK / AT RISK")

Recommended Order Units = SUM(replenishment_recommendations[recommended_order_quantity])

Average Inventory Coverage = AVERAGE(replenishment_recommendations[coverage_days_proxy])

A-Class SKU Count =
CALCULATE(COUNTROWS(abc_inventory_classification),
    abc_inventory_classification[abc_class] = "A")

B-Class SKU Count =
CALCULATE(COUNTROWS(abc_inventory_classification),
    abc_inventory_classification[abc_class] = "B")

C-Class SKU Count =
CALCULATE(COUNTROWS(abc_inventory_classification),
    abc_inventory_classification[abc_class] = "C")

A-Class Reorder Count =
CALCULATE([SKUs Requiring Reorder],
    TREATAS(
        CALCULATETABLE(VALUES(abc_inventory_classification[local_sku_id]),
            abc_inventory_classification[abc_class] = "A"),
        replenishment_recommendations[local_sku_id]
    ))

Critical Cases =
CALCULATE(COUNTROWS(supply_chain_priority_matrix),
    supply_chain_priority_matrix[management_priority] = "CRITICAL")

High Priority Cases =
CALCULATE(COUNTROWS(supply_chain_priority_matrix),
    supply_chain_priority_matrix[management_priority] = "HIGH")

Medium Priority Cases =
CALCULATE(COUNTROWS(supply_chain_priority_matrix),
    supply_chain_priority_matrix[management_priority] = "MEDIUM")

Needs Review Supplier Cases =
CALCULATE(COUNTROWS(supply_chain_priority_matrix),
    supply_chain_priority_matrix[supplier_tier] = "Needs Review")
```

`A-Class Reorder Count` uses TREATAS because a filter on the separate ABC snapshot does not flow backward through `local_skus`. For ABC/priority cross-slicers on Action Center, use columns from `supply_chain_priority_matrix` consistently, and use its own fields for the action table. Inventory status has **no zero-inventory status** in this snapshot: Stockout SKUs tests zero units and may be 0, whereas Low Stock SKUs is the explicit policy label. Safety stock / reorder point are *per SKU*; the average measures have a different interpretation from the single-SKU measure.

## Simulated procurement and supplier outcomes

```DAX
Purchase Orders = COUNTROWS(purchase_orders)

Ordered Commitment =
SUMX(purchase_orders,
    purchase_orders[ordered_quantity] * purchase_orders[procurement_unit_cost])

Supplier On-Time % =
DIVIDE(SUM(supplier_scorecard[on_time_receipts]),
       SUM(supplier_scorecard[purchase_orders]))

Supplier Fill % =
DIVIDE(SUM(supplier_scorecard[received_units]),
       SUM(supplier_scorecard[ordered_units]))

Average Actual Lead Time =
DIVIDE(SUMX(supplier_scorecard,
    supplier_scorecard[avg_actual_lead_days] * supplier_scorecard[purchase_orders]),
    SUM(supplier_scorecard[purchase_orders]))

Supplier Lead-Time Variability (selected supplier) =
IF(HASONEVALUE(suppliers[supplier_id]), MAX(supplier_scorecard[lead_sd_days]))

Supplier Score (selected supplier) =
IF(HASONEVALUE(suppliers[supplier_id]),
    MAX(supplier_scorecard[supplier_score_assumed_weights]))
```

All supplier measures represent the **simulated scenario**. On-time and fill use pooled numerator/denominator, not an unweighted mean of supplier percentages. Lead time is weighted by PO count using rounded scorecard means, so reconcile within rounding to the receipt-level calculation. The score is a relative assumed-weight score: no global sum/mean card. Show by supplier only. `Ordered Commitment` is order value, not invoices or realized spending.

## KPI provenance and limits

| KPI family | Business meaning | Main source and lineage | Limitation |
| --- | --- | --- | --- |
| Sold / daily sold | historical sales proxy and average per observed date | daily_operations; published synthetic SOURCE | Not uncensored customer demand; daily average changes with filters |
| Forecast / MAE / WAPE / baseline | future expected units and held-out forecast errors | Ridge-derived forecast, DERIVED backtest | 14-day forecast aggregate; test errors from historical rolling origins, modest improvement |
| Inventory / status / coverage | latest source snapshot and planning state | SOURCE synthetic snapshot + DERIVED policy | Not live stock ledger; coverage/thresholds use assumptions |
| ABC counts / A reorder | 2023 sales-value proxy portfolio and overlap | DERIVED from synthetic source | Not gross margin or genuine product valuation |
| Priority cases | rule-defined management queue | DERIVED combined snapshot | No demonstrated action/outcome; no routine rows in this export |
| Procurement / supplier | scenario commitments and receipt outcomes | SIMULATED events; DERIVED relative score | No real-world supplier claims; score weights assumed |

Never display these as actual savings, implemented orders or observed suppliers. Every numeric KPI above is defined by its code block; add a tooltip note from this table on its visual. See `POWERBI_VALIDATION_CHECKLIST.md` for precise unfiltered anchors.
