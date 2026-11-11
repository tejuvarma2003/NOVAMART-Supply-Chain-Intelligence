# Phase 5 — exploratory supply-chain analysis

## Objective, data, and workflow

Understand sales, inventory, price/promotion, location/category, and **simulated** procurement patterns before designing forecasting and inventory policies. The reproducible notebook is `notebooks/01_supply_chain_eda.ipynb`; its computations and nine saved figures come from `src/phase5_eda.py`. Run from the repository root with `python src/phase5_eda.py` and `python src/validate_phase5.py`. The notebook code cells were also executed sequentially end to end in one Python process. The notebook's interactive Jupyter kernel could not start in this environment because local network interface access was denied; the equivalent Python cells and script completed successfully.

The public Kaggle source is itself **synthetic**. `daily_operations` has 76,000 complete store-local-SKU days from 2022-01-01 to 2024-01-30, 100 local SKUs, 5 replenishment locations, and no missing values or duplicate keys. Five categories are present. The separately generated 5,299 POs, 5,299 receipts, and 6 suppliers are a **SIMULATED NOVAMART PROCUREMENT SCENARIO**. Procurement events do not reconstruct the published stock ledger.

## Demand and sales findings (publisher synthetic source)

- Total fulfilled units sold: **6,750,876**. Groceries contribute **3,127,335**, the largest category total; their mean is **102.87 units per SKU-day**. Category totals reflect unequal category sizes, so compare normalized means when discussing demand intensity.
- `S002` has the largest location total (**1,386,126 units**), while `S004` has **1,308,191**. These differences are descriptive, not evidence of superior operating performance.
- The top ten local SKUs account for **12.04%** of total sold units. Highest local SKU by units is `S001_P0003` (**82,721**); lowest is `S004_P0018` (**46,967**). The distribution is not dominated by a single SKU.
- Daily local-SKU coefficient of variation (sample SD / mean) has median **0.470**, ranging **0.338–0.580**. SKU-level variability matters for forecast errors and later safety stock; the reported spread should be assessed alongside mean volumes and stock constraints. There are **406 zero-sales SKU-days**, which coincide with the 406 zero-inventory observations in this dataset.
- Weekday mean sales per SKU-day range from **87.87 Monday** to **89.55 Wednesday**. The aggregate weekday differences are small; do not assume strong weekly seasonality. Monthly totals vary, but the final January 2024 period is missing one day and only about two annual cycles are available. The monthly and smoothed daily plots support exploration of changes, not a firm claim about recurring annual seasonality.

## Inventory and exploratory coverage (publisher synthetic source)

- There are **406 zero-inventory SKU-day snapshots** across 69 local SKUs. They are warning signals, not confirmed lost sales or measured stockout durations.
- Latest source date is **2024-01-30**. The 100 latest snapshots sum to **29,049 units**. Source `inventory_units` has median **227** per SKU-day, with a maximum of **2,267**. Average snapshot inventory differs by location: `S002` about **332.01** units per SKU-day versus `S001` about **277.66**.
- Latest inventory divided by the prior 28 days' average sales gives median **2.824 coverage days**; **90 of 100 local SKUs** fall under an illustrative 7-day screen. This unusually broad exception rate may reflect how the dataset was generated or when snapshots were taken. It is a descriptive screening tool, not an optimized reorder point or prediction of lost sales.
- Inventory snapshots lack the stock movement ledger needed to reconcile on-hand amounts to sales and receipts. Simulated procurement cannot repair that gap and is intentionally analyzed separately.

## Price, discount, and promotion associations (publisher synthetic source)

- Median listed price is **64.50** in unspecified currency (5th–95th percentile: **15.30–137.33**). Price varies across dates and local SKUs; pooling all rows in a simple scatterplot can obscure product differences.
- Promotion-flagged SKU-days average **103.10 units sold** versus **81.83** without the flag. Discount values of 0/5 average about **81.57/81.70**, while values of 15/20/25 average about **102.88/103.78/103.59** units. These are associations; no causal promotion lift is claimed.
- Pooled Pearson correlation with units sold is **0.227** for promotion, **0.184** for discount, **−0.015** for listed price, **0.235** for inventory, and **0.833** for publisher-estimated demand. Product mix, price scale, and stock constraints affect these relationships. The publisher-estimated demand field is **not** accepted as verified customer demand or the Phase 6 target; it is lower than observed sales on 21,000 source rows.

## Category and location planning context

Groceries lead both total units and average units per SKU-day; Furniture's average is **64.38**, versus **102.87** for Groceries. Category-specific demand intensity and variability can inform grouping in later diagnostics. Location sales totals are relatively close, while mean inventory snapshots differ more; planners would compare coverage and SKU composition before changing stock allocations. There is no evidence of a shared global product catalog across stores because source product IDs conflict in category.

## SIMULATED NOVAMART PROCUREMENT SCENARIO

- The **5,299** POs represent **348,263,386.82** of ordered commitment in unspecified currency, not payments or savings. Activity clusters around the fixed 14-day review schedule; monthly count changes partly reflect calendar alignment, not a discovered procurement season.
- **4,923** receipts are complete and **376** partial. **3,316** arrive on or before their expected dates, **1,983** later. Actual simulated lead times range **2–19 days**.
- Calculated supplier on-time percentages range **57.67% (`SUP-05`) to 68.81% (`SUP-01`)**. `SUP-05` has mean actual lead time **11.03 days** and population lead-time SD **2.52 days**. `supplier_eda_summary.csv` also includes PO count, late percentage, unit-weighted receipt fill, positive delay, and ordered commitment. These outcomes arise from documented generator assumptions; they are neither real supplier observations nor a final composite supplier score.

## Implications for Phase 6 forecasting

The full daily panel supports time-aware SKU-by-location evaluation. Check a simple baseline before a complex model. The provisional 14-day horizon remains sensible for review, with 7- and 30-day sensitivity to be tested. SKU variability and month-to-month changes warrant segment-level error diagnostics; pooled weekday averages provide weak evidence for a large weekday effect. Calendar and past observed sales are plausible inputs. Promotion and listed price can be used only when future values are known at decision time; same-day publisher demand, inventory, actual weather, competitor price, and unannounced promotions create availability or leakage risk. This phase created **no** lag features, train/test split, forecasts, or accuracy results.

## Implications for Phase 7 inventory optimization

Coverage and zero-stock observations suggest where to investigate, while sales variability suggests that one rule may not suit every local SKU. Simulated lead-time outcomes can illustrate scenario calculations later. Any safety stock, reorder point, EOQ, or order quantity must declare service level, costs, timing, and data provenance; none were calculated here.

## Artifacts, validation, and limitations

Nine PNG charts are saved in `images/eda/` (trend, monthly, weekday, category/location, SKU variability, inventory/coverage, promotion/discount, simulated supplier delivery, and source correlations). Reusable summaries: `sku_demand_profile.csv`, `inventory_eda_summary.csv`, `supplier_eda_summary.csv`, plus `phase5_metrics.json`.

`src/validate_phase5.py` passed: 76,000 rows, 100 SKUs, full date span, **6,750,876** units sold and **406** zero-stock rows reconcile with the SQLite source; supplier on-time counts, percentages, lead times, fill, and commitment reconcile with Phase 4's SQL export; source versus simulated lineage is checked; all 13 summaries/charts have identical hashes after a rerun. Chart labels and summaries are produced from the same calculations. These checks establish computational consistency, not external validity of synthetic data.
