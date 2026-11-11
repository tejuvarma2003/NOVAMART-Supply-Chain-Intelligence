# Phase 7 inventory-planning assumptions

The public retail data is itself synthetic. The following distinctions apply to every output. No purchase orders are placed, and the recommendations do not reconcile to the separately simulated historical procurement events.

| Input / policy | Value or rule | Provenance | Limitation |
| --- | --- | --- | --- |
| Planning date | 2024-01-30 | SOURCE latest snapshot date | Inventory snapshot timing within day unknown. |
| Inventory position proxy | Latest `inventory_units` by local SKU | SOURCE | No verified open orders, allocations, backorders, or transaction ledger. |
| Demand rate | Sum of 14 daily forecasts / 14 | FORECAST, then DERIVED | Future fulfilled sales proxy; not unconstrained orders. |
| Supplier lead time | Primary `sku_supplier_map.expected_lead_time_days` | SIMULATED | Fixed expected days; variation not included in primary safety-stock formula. |
| Daily demand error SD | Population SD of signed out-of-sample residuals per SKU from validation and test | DERIVED from FORECAST errors | Direct multi-horizon residuals overlap in time and need not be independent daily errors. |
| Cycle service level | 95%; one-sided normal z = 1.645 | ASSUMED policy | Intended target, not historically achieved service. |
| Ordering cost | 75 per PO, unspecified scenario currency | ASSUMED | No actual administrative cost supplied. |
| Annual carrying rate | 20% of simulated procurement cost per unit | ASSUMED | No observed holding costs. |
| Annual demand proxy | Forecast daily units × 365 | DERIVED from FORECAST | Stationary annualization of a short horizon; not an annual forecast. |
| Review period | 14 days | ASSUMED, aligned to forecast horizon | A periodic-review target paired with a continuous-review trigger for demonstration. |
| EOQ sensitivity | Ordering cost 40/75/120 and carrying rate 15%/20%/30% | ASSUMED | Scenario range, no financial optimum claim. |

Formulas use unrounded fractional units until the final proposed physical order:

- Lead-time demand = daily forecast × expected lead days.
- Safety stock = `1.645 × daily residual SD × sqrt(expected lead days)`; normal independent-error approximation.
- Reorder point = lead-time demand + safety stock.
- Target stock = `(lead days + 14 review days) × daily forecast + safety stock`.
- EOQ reference = `sqrt(2 × (daily forecast × 365) × 75 / (procurement unit cost × 0.20))`.
- Inventory status, evaluated in order: **STOCKOUT** if inventory ≤ 0; **REORDER REQUIRED** if inventory ≤ reorder point; **EXCESS INVENTORY** if inventory > 2 × target stock; **LOW STOCK / AT RISK** if inventory < target stock; else **HEALTHY**. The factor 2 is an illustrative upper coverage screen, not a validated excess threshold.
- Proposed order = `ceil(max(0, target stock − inventory proxy))` **only when inventory ≤ reorder point**; otherwise zero. EOQ is shown as a cost-policy reference, not forced as the order quantity. Actual minimum order quantities, pack sizes, budgets, and open POs are unknown.
- Priority: **CRITICAL** for STOCKOUT, **HIGH** for REORDER REQUIRED, **MEDIUM** for LOW STOCK / AT RISK or EXCESS INVENTORY, **NO ACTION** for HEALTHY. Excess is a review exception, not a purchase action.
- **POTENTIAL SLOW-MOVING** requires forecast daily demand at or below the 25th percentile of this 100-SKU panel **and** inventory coverage > `2 × (lead days + 14)`; it does not mean obsolete. Undefined coverage at zero forecast is explicitly handled rather than treated as a number.

The 95% cycle service target changes z, hence safety stock and reorder point; for a fixed uncertainty SD and lead time, higher z increases both. Lead-time variability would require another validated uncertainty term or a scenario sensitivity rather than silently treating simulated supplier lead-time SD as measured.
