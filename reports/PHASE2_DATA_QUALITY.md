# Phase 2 — dataset validation and ERP design

## Source and reproducibility

Candidate: [Retail Store Inventory and Demand Forecasting](https://www.kaggle.com/datasets/atomicd/retail-store-inventory-and-demand-forecasting), publisher `atomicd` / Wavelet, Kaggle version 8. Kaggle metadata lists **Apache 2.0** and explicitly calls the dataset **synthetic**; its description says it corrects identifiers in an earlier synthetic dataset and adds `Epidemic`. All measured figures below are properties of this published simulation, not observed NOVAMART operations. The archived original CSV is retained unchanged in `data/raw/atomicd_retail_inventory_v8.zip`; `src/profile_phase2.py` regenerates `phase2_profile.json` from it. Archive SHA-256 is recorded in the JSON.

## Validation results

| Check | Observed result |
| --- | --- |
| Size and grain | 76,000 rows × 16 columns; exactly one row per Date × Store ID × Product ID |
| Dates | 2022-01-01 through 2024-01-30, 760 consecutive daily dates |
| Coverage | 5 stores × 20 product IDs = 100 store/product series, each 760 days; 100 rows/day, no missing grid cells |
| Categories | Groceries 30,400; Furniture 13,680; Clothing 12,160; Toys 10,640; Electronics 9,120 rows |
| Regions | North 30,400; South 15,200; East 15,200; West 15,200 rows |
| Missing, duplicate rows, duplicate grain keys | 0 in every case |
| Invalid numerical values | No negative values in measured numeric columns, no price ≤ 0, no discount outside 0–100, no invalid binary flags |
| Inventory | min 0, Q1 136, median 227, Q3 408, P95 756, max 2,267; 406 zeros |
| Units sold | min 0, Q1 58, median 84, Q3 114, P95 169, max 426; 406 zeros |
| Demand | min 4, Q1 71, median 100, Q3 133, P95 188, max 430; no zeros |
| Price | min 4.74, Q1 32.00, median 64.50, Q3 95.83, P95 137.33, max 228.03 |
| Restock/discount | `Units Ordered` has 47,107 zeros; `Discount` values 0, 5, 10, 15, 20, 25; `Promotion` 25,000 ones |
| Calendar/external fields | `Seasonality` Winter/Spring/Summer/Autumn matches calendar months (0 conflicts); Weather Condition Cloudy/Sunny/Rainy/Snowy; `Epidemic` 15,200 ones |

**Structural defect:** All 20 product IDs appear under multiple categories across different stores. Category is constant within each store/product pair, but `Product ID` is **not a globally reliable product key**. The data cannot support one shared company-wide product dimension keyed only by `Product ID` without resolving or splitting these identities. A safe initial key is `(Store ID, Product ID)` or a surrogate `novamart_sku_id` assigned to that pair; this treats identically named IDs in different stores as distinct items and weakens cross-store product comparisons. It does not establish that the original products are truly different.

**Interpretation defect:** 21,000 rows have Units Sold greater than `Demand`, though Units Sold never exceeds Inventory Level. Thus `Demand` cannot be treated as a verified count of realized orders or a perfect unconstrained-demand ground truth. It is labeled a daily **estimated demand** by the publisher. The 406 zero-inventory rows also have zero sales; observed sales are potentially stock constrained. Inventory can vary between dates, but `Units Ordered` is not a purchase-order or receipt ledger: the daily inventory change cannot reliably be reconciled using sales and orders alone. Historical stockout incidence, fill rate, lead times, and on-time delivery cannot be asserted from these fields.

## Exact public columns and data dictionary

Types are pandas CSV inference before conversion; `Date` will be parsed to a date in Phase 3. Every row below is **public dataset content, itself synthetic according to the publisher**.

| Original field | Inferred type | Meaning / planned cleaned name | Treatment |
| --- | --- | --- | --- |
| Date | object | `snapshot_date` | Parse ISO date; daily grain |
| Store ID | object | `source_store_id` | Store key |
| Product ID | object | `source_product_id` | Local ID, not global SKU key |
| Category | object | `category` | Attribute of store/product pair pending identity decision |
| Region | object | `region` | Stable store attribute |
| Inventory Level | int64 | `inventory_units` | Snapshot; stock timing unspecified |
| Units Sold | int64 | `units_sold` | Daily observed sales, possibly censored by stock |
| Units Ordered | int64 | `units_ordered_source` | Daily restocking indicator/amount; no PO identity or receipt proof |
| Price | float64 | `listed_price` | Daily price; currency and discount application unspecified |
| Discount | int64 | `discount_percent_source` | Values 0–25; unit appears percentage but confirm in project assumptions |
| Weather Condition | object | `weather_condition` | Day-specific label; future values not known without forecasts |
| Promotion | int64 | `promotion_flag` | Binary; future plans not supplied |
| Competitor Pricing | float64 | `competitor_price` | Day-specific comparison price |
| Seasonality | object | `seasonality_label` | Calendar season |
| Epidemic | int64 | `epidemic_flag` | Binary simulated event, availability at forecast time unclear |
| Demand | int64 | `estimated_demand_source` | Publisher's estimate, not verified customer orders |

**Derived from published fields, not additional observed facts:** parsed date, day-of-week/month, canonical store/product pair key, store-product category, `sales_value_proxy = units_sold × listed_price` (not audited revenue), rolling historical sales features, lagged demand features, inventory coverage estimate, and a cautiously labeled stock-constraint flag. Any discount-adjusted revenue needs an explicit price assumption.

**Synthetic ERP extensions to create only in a later approved phase:** suppliers, supplier/product assignments, unit acquisition costs, lead-time assumptions, purchase-order headers/lines and dates, receipts, promised dates, actual shipment/delivery dates, warehouse identifiers if a store is modeled as replenishment location, and optionally customer/order records. Mark provenance on every table and derived output. Do not infer synthetic supplier service performance as an empirical finding.

## Forecasting feasibility and recommendation

The actual file fully supports a **daily Store ID × local Product ID** panel: 100 uninterrupted series of 760 days. It supports SKU × replenishment location × date only if stores are explicitly treated as the inventory-holding locations; it does not prove separate warehouses or a global SKU catalog. Forecast `Units Sold` as observable fulfilled sales, while comparing `Demand` as an alternative publisher-provided estimated target in sensitivity analysis. Do not use same-day `Demand`, `Inventory Level`, `Units Ordered`, actual weather, competitor price, or unannounced promotions as features for a future forecast; their future availability is unproven. Evaluate a chronological holdout and a seasonal naive baseline in Phase 6.

**Proposed primary horizon: 14 days**, with 7-day and 30-day evaluation as sensitivity checks. Two full weeks include repeated day-of-week patterns and make a plausible periodic replenishment review window. Seven days may be too short for variable supplier lead times, while 30 days is harder to defend for a reorder decision before lead-time evidence exists. The horizon remains provisional until synthetic lead-time policy and business review cadence are agreed. There is enough history for repeated 14-day temporal evaluation, but only about two annual cycles, so annual seasonality claims are weak. Aggregate daily predictions to horizon totals for ordering; avoid turning a forecast into a service-level guarantee.

## Proposed ERP-style schema (design only)

| Table | Grain / key | Provenance and relationship |
| --- | --- | --- |
| `dim_store_location` | one per Store ID | Public store ID and stable region; later role as replenishment location is a modeled assumption |
| `dim_product_local` | one per `(Store ID, Product ID)` | Public pair and its stable category; surrogate SKU key, pending global-ID resolution |
| `fact_store_sku_day` | one per date × local SKU | Public daily sales, estimated demand, inventory snapshot, units ordered, price, discount, weather, promotion, competitor price, seasonality, epidemic; FK to location and product-local |
| `dim_supplier` | one per synthetic supplier | Synthetic, created later |
| `bridge_supplier_sku` | one per supplier × local SKU | Synthetic source assignment, cost and lead-time policy, created later |
| `purchase_order` + `purchase_order_line` | PO header + SKU lines | Synthetic later; distinguish order placement from receipt |
| `shipment` + `receipt` | shipment / received PO line | Synthetic later; promised versus actual dates and quantities |

Keep synthetic tables physically distinct and add a `data_origin` / `scenario_id` in modeled outputs. A full sales-order/customer table would be wholly synthetic and is optional; aggregate daily sales should **not** be backfilled with fabricated order IDs presented as source transactions. Do not create an independent warehouse layer unless the scenario explicitly calls for transfers or store supply relationships.

## Lineage

```text
Kaggle synthetic source ZIP
  -> typed/validated public fields (local store-product keys)
  -> derived calendar, historical aggregates, sales-value proxies
  -> separately labeled simulated supplier / PO / shipment extensions
  -> SQLite dimensions and daily facts, with provenance
  -> SQL analyses, time-aware ML, inventory scenarios, BI exports
```

## Quality verdict and Phase 3 gate

**Conditionally usable for a portfolio scenario**: complete daily panel, useful sales and inventory variables, and manageable size. Clean by parsing dates, assigning local SKU identity, validating ranges/keys, and preserving the unmodified archive. Exclude `Demand` as if it were verified orders, exclude a global product dimension keyed only by Product ID, and exclude same-day unknown future variables from operational forecast features. Do not claim observed supplier performance, actual fill rate, audited revenue, true realized stockouts, or realized cost savings. Inventory policy is a scenario calculation until real lead times, receipts, carrying/ordering costs, and stock timing are available.

**Approval choices:** (1) Accept this publicly published **synthetic** dataset despite the original preference for real observed retail records, or choose a different public foundation; (2) approve store-specific SKU identity or choose a documented reconciliation approach; (3) approve stores as replenishment locations and provisional 14-day horizon; (4) decide whether optional fully synthetic customer/sales-order entities are needed. No Phase 3 preparation has run.
