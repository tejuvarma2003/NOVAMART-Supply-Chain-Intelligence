# Phase 8 — ABC inventory and simulated supplier performance

## Business objective and lineage

ABC identifies local SKUs that contribute most to a **historical sales-value proxy**. Joining it to Phase 7 stock flags and supplier scenario metrics creates a management review queue. The public sales and prices are publisher-generated synthetic data. Suppliers, procurement, delivery outcomes, and supplier scores are **additional simulated scenario analytics**. The forward forecast and inventory recommendations remain model/assumption outputs, not implemented actions.

## ABC definition and actual results

Use the complete calendar year **2023-01-01 through 2023-12-31**, 365 daily records for each of 100 local SKUs. `sales_value_proxy_2023 = SUM(units_sold × listed_price)` for each SKU; no annualization is needed. Price is the published listed price, with unspecified currency and unknown realized discount treatment, so this is neither audited revenue nor procurement cost/COGS. Total proxy value is **216,293,681.43** in unspecified currency.

Sort descending by proxy value with local SKU ID as a deterministic tie-break. Let `prior cumulative share = cumulative value share − current SKU share`. Class **A** when prior share <80%, **B** when prior share ≥80% and <95%, otherwise **C**. Thus the SKU that crosses each boundary belongs to the preceding class. The rule approximates, but need not exactly equal, 80/15/5. It does not force class sizes.

| ABC | Local SKUs | Share of 2023 proxy value | Share of 2023 sold units | Reorder-required now |
| --- | ---: | ---: | ---: | ---: |
| A | 60 | 80.881% | 58.976% | 57 |
| B | 24 | 14.505% | 24.922% | 24 |
| C | 16 | 4.614% | 16.102% | 16 |

All 100 local SKUs receive one class. A represents value importance, **not** demand volatility or automatic entitlement to higher safety stock. The three A SKUs above their reorder point remain low relative to target under Phase 7; they receive no order under that policy. No previous recommendations were altered.

## Supplier KPIs and transparent score

The six suppliers and 5,299 POs/receipts are simulated. Supplier KPIs are recalculated from each joined PO/receipt, using Phase 4 definitions: ordered commitment = sum ordered units × PO unit cost; on-time = receipts dated on/before promise ÷ eligible receipts; late is the complement; fill = total units received ÷ total units ordered; actual lead = receipt date − PO date; variability is population SD of actual lead days; delay performance uses mean `max(0, actual date − promised date)` across **all** receipts. These reconcile with Phase 4 `supplier_performance.csv` within reporting rounding.

For each metric across six suppliers, min-max normalize to 0–100. Higher on-time and fill score better; lower actual lead-time SD and positive delay score better. If all values tie, give everyone 100 for that component. The **assumed** base score is **40% on-time + 30% fill + 20% consistency + 10% delay**. Spend is displayed as exposure but excluded from quality scoring. This is a relative score within these six simulated suppliers, not a calibrated external rating. Tier rules: score ≥70 **Strong**, 40–<70 **Moderate**, <40 **Needs Review**.

| Simulated supplier | POs | On-time | Fill | Mean lead days | Lead SD days | Base score | Tier |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| SUP-01 Northstar Goods | 901 | 68.81% | 99.71% | 5.01 | 1.05 | 100.00 | Strong |
| SUP-02 Cedar Wholesale | 900 | 59.67% | 99.26% | 7.07 | 1.50 | 45.35 | Moderate |
| SUP-03 Harbor Supply | 901 | 58.93% | 98.68% | 9.00 | 2.09 | 15.66 | Needs Review |
| SUP-04 Summit Distribution | 901 | 68.15% | 99.30% | 6.03 | 1.06 | 86.41 | Strong |
| SUP-05 Pioneer Trading | 848 | 57.67% | 98.60% | 11.03 | 2.52 | 0.00 | Needs Review |
| SUP-06 Willow Merchants | 848 | 61.91% | 98.85% | 8.03 | 1.58 | 41.36 | Moderate |

The 0 and 100 endpoints arise from relative min-max normalization on a small six-supplier set. They do **not** imply literal zero or perfect supplier quality. Alternative weights **25% on-time + 35% fill + 25% consistency + 15% delay** leave all six ranks unchanged (0 rank changes), though score values shift. Rankings can still change under other plausible weights or new outcomes; the tier cutoffs are analytical assumptions.

## Combined management priority and examples

The combined view has **one row per local SKU** and retains Phase 7 `recommendation_priority` separately. New `management_priority` precedence is:

1. **CRITICAL:** A + stockout/reorder required + supplier Needs Review.
2. **HIGH:** A + stockout/reorder required, or B + stockout/reorder required + supplier Needs Review.
3. **MEDIUM:** any other stockout/reorder required, or another A inventory exception.
4. **ROUTINE:** remainder.

| Management priority | Local SKUs |
| --- | ---: |
| CRITICAL | 23 |
| HIGH | 36 |
| MEDIUM | 41 |
| ROUTINE | 0 |

The absence of routine cases follows Phase 7's unusually broad 97/100 reorder flags; it is not a general supply-chain benchmark. The [high-priority action file](high_priority_supply_chain_actions.csv) lists the 59 Critical/High cases. Examples within this **scenario**: `S003_P0011` (A, reorder required, SUP-03 Needs Review, 2023 value proxy 4,059,537.36), `S004_P0009` (A, reorder required, SUP-03, 3,880,614.55), and `S005_P0009` (A, reorder required, SUP-05, 3,787,774.72). A manager would review stock and supplier options first; the view does not quantify actual loss or instruct an automatic supplier change.

## Artifacts and validation

`src/abc_supplier_analysis.py` generates `abc_inventory_classification.csv`, `supplier_scorecard.csv`, `supply_chain_priority_matrix.csv`, `high_priority_supply_chain_actions.csv`, `phase8_summary.json`, and six charts in `images/abc_supplier/`. `notebooks/04_abc_supplier_analysis.ipynb` explains the workflow. `POWERBI_DATA_MODEL_GUIDE.md` prepares relationships for Phase 9; no dashboard was built.

`src/validate_phase8.py` passed the 100-class uniqueness and full-year checks, recomputed value/share/monotonic cumulative percentages and boundary classes, reconciled six supplier KPI rows to Phase 4, checked score directions and weights, preserved all 100 primary-supplier joins, recalculated priorities, confirmed the Phase 7 file hash was unchanged, and reproduced all 11 Phase 8 outputs. Both ABC value and supplier tiers rely on synthetic data and assumptions; no savings or real supplier assessment is claimed.
