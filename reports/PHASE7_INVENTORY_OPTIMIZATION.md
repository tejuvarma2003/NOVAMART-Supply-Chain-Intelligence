# Phase 7 — inventory policy and replenishment scenario

## Purpose and lineage

The Phase 6 Ridge forecast supplies 14 expected daily units for every local SKU. Phase 7 combines their 14-day mean with the **2024-01-30 source synthetic inventory snapshot**, SKU out-of-sample forecast residual variation, and **simulated** primary supplier lead times/costs. A documented **assumed** service level and costs turn these inputs into a planning scenario. See [INVENTORY_ASSUMPTIONS.md](INVENTORY_ASSUMPTIONS.md) for the full assumption table, formulas, status precedence, and provenance. Neither the source inventory nor historical simulated procurement was changed.

## Policy, formulas, and operational meaning

The assumed cycle service target is **95%**, represented by one-sided normal **z = 1.645**. Daily demand rate is the unrounded 14-day forecast sum divided by 14. Lead-time demand is rate × simulated expected lead days. Safety stock is `1.645 × SKU out-of-sample daily signed-error population SD × sqrt(lead days)`. This assumes approximately independent daily forecast errors and fixed lead time; Phase 6 direct 14-day errors may be serially correlated, so the number is a scenario approximation, not calibrated service assurance.

**Reorder point = lead-time demand + safety stock.** Compare it to the latest on-hand source snapshot as an *inventory position proxy*. No verified open PO, backorder, or allocation is included. Crossing the reorder point triggers review; it is not the number to buy.

**Target stock = (lead days + 14 review days) × forecast daily rate + safety stock.** Only a SKU at or below the reorder point receives `ceil(max(0, target − current inventory))` physical units. An item above the point can be flagged low relative to target but gets no order under this rule. This combines a continuous-review trigger with a 14-day periodic-review target for a teachable scenario; an operating business should settle one formal policy and inventory-position definition before implementation.

**EOQ reference = sqrt(2 × annualized forecast demand × assumed 75/order ÷ annual holding cost per unit)**, with annualized demand = daily rate × 365 and holding cost = simulated unit procurement cost × assumed 20% annual carrying rate. Currency is unspecified. EOQ is a separate benchmark, **not forced into every order quantity**. The annualization, cost, and holding rate are not observed finances.

## Status and priority rules

Sequentially: stock ≤ 0 → **STOCKOUT**; otherwise stock ≤ reorder point → **REORDER REQUIRED**; otherwise stock > 2 × target → **EXCESS INVENTORY**; otherwise stock < target → **LOW STOCK / AT RISK**; else **HEALTHY**. Priorities are CRITICAL, HIGH, MEDIUM, MEDIUM, NO ACTION respectively. An excess item receives a review flag but never a purchase. Potential slow-moving requires daily forecast in the bottom quarter of 100 SKUs plus coverage greater than twice (lead + review days); none qualify under this snapshot. This does **not** establish that no slow-moving items exist in reality.

## Calculated scenario results

| Outcome | Result |
| --- | ---: |
| Local SKUs evaluated | 100 |
| STOCKOUT / CRITICAL at latest snapshot | 0 |
| REORDER REQUIRED / HIGH | 97 |
| LOW STOCK / AT RISK / MEDIUM | 3 |
| HEALTHY or EXCESS | 0 |
| Proposed physical replenishment units | 180,766 |
| Mean scenario safety stock per local SKU | 175.48 units |
| Mean EOQ reference | 891.53 units |
| Mean forecast-based inventory coverage | 3.27 days |
| Potential slow-moving by strict screen | 0 |

The **97/100** flag rate is unusually broad. It reflects low publisher-generated final stock relative to forecast sales, the 5–11 day simulated lead times, and the assumed 95% buffer. Treat it as an exception-screen outcome requiring review of source snapshot timing, source generation, and policy assumptions. The **180,766 units** are proposals, not issued or implemented POs. The management exception export includes all 100 SKUs because even the three above the reorder point are below target; those three have **zero** proposed order under the defined trigger. No savings or realized service level is claimed.

## Three manually checked examples

All examples use the same z = 1.645 and 14-day review target; EOQ uses assumed 75/order and 20% annual holding rate. Unrounded values drive arithmetic, then only the final order is ceiled.

| SKU | Forecast 14d → daily | Lead days → lead demand | Error SD → safety stock | ROP vs stock | EOQ reference | Target → final order and action |
| --- | --- | --- | --- | --- | ---: | --- |
| `S001_P0001` | 1,224.05 → 87.43 | 5 → 437.16 | 35.25 → 129.66 | 566.82 vs 383 | 717.13 | 1,790.87 → **1,408**, REORDER REQUIRED |
| `S001_P0003` | 1,662.21 → 118.73 | 9 → 1,068.56 | 44.36 → 218.89 | 1,287.45 vs 434 | 920.12 | 2,949.66 → **2,516**, REORDER REQUIRED |
| `S001_P0010` | 929.86 → 66.42 | 6 → 398.51 | 29.57 → 119.14 | 517.66 vs 518 | 482.16 | 1,447.52 → **0**, LOW STOCK / AT RISK |

`S001_P0010` illustrates why being below a review target does not automatically trigger a PO. `S001_P0003` illustrates why EOQ and order quantity differ: EOQ is a cost benchmark under assumptions, while the proposed order closes a target-stock gap.

## EOQ sensitivity and interpretation

Across the 100 SKUs, mean EOQ under ordering cost **40** and holding rate **30%** is **531.61** units; at **120** and **15%** it is **1,302.16**. The base 75/20% mean is **891.53**. Higher ordering cost increases EOQ; a higher carrying rate decreases it. The wide range demonstrates why an EOQ computed with assumed costs should not be described as a verified optimum. `reports/eoq_sensitivity.csv` contains all nine combinations.

## Outputs and verification

`reports/replenishment_recommendations.csv` includes 100 local-SKU rows, full inputs and intermediate calculations, statuses, integer order proposals, and explicit lineage fields. `reports/inventory_exceptions.csv` is the attention view. `reports/phase7_kpi_summary.json` and `reports/eoq_sensitivity.csv` hold aggregate and sensitivity results. Six PNGs under `images/inventory/` show status, inventory versus reorder point, safety stock by category, coverage, largest proposed orders, and EOQ sensitivity. The notebook `notebooks/03_inventory_optimization.ipynb` explains the workflow; `src/inventory_optimization.py` builds it.

`src/validate_phase7.py` passed 100 unique SKUs, complete forecast/error/supplier joins, positive lead times and EOQ, nonnegative safety stock/reorder points/orders, unrounded intermediate formulas, status and priority logic, exact current snapshot match, unchanged source-file hash, three hand-check examples, and byte-identical outputs on a rerun.

Limitations: source retail data and additional supplier scenario are synthetic; the inventory snapshots do not reconcile to procurement; lead times are assumed; normal independent-error safety stock is approximate; annual demand and financial costs are planning assumptions; no open-order position, packs, capacity, budget, or real service performance is modeled. Phase 8 classification and supplier scoring remain unstarted.
