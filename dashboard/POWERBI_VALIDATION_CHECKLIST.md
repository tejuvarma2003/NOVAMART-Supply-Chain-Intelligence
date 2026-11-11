# Phase 9 Power BI validation checklist

These anchors were recomputed by `python src/prepare_phase9.py` against copied files and upstream hashes; `phase9_validation.json` records the checks. They are **unfiltered**, except forecast test metrics explicitly filter `split = test`. No Power BI UI or DAX execution was possible in this Linux environment. Mark each item in Windows after building.

| Check with all slicers cleared | Expected | Test in Power BI |
| --- | ---: | --- |
| locations / local_skus / suppliers | 5 / 100 / 6 | Count rows and unique keys |
| daily_operations / forecast / holdout | 76,000 / 1,400 / 14,000 | Table row count |
| purchase_orders / receipts | 5,299 / 5,299 | Count rows; receipts are simulated |
| Total Units Sold | 6,750,876 | Historical all-date card |
| 14-Day Forecast Units | 126,137.36 | Unfiltered forecast card, rounding to 2 decimals |
| Latest Inventory Units | 29,049 | One current row per local SKU |
| SKUs Requiring Reorder | 97 | Status = REORDER REQUIRED |
| Recommended Order Units | 180,766 | Whole physical units, proposed |
| ABC A / B / C | 60 / 24 / 16 | Total 100; sales-value proxy |
| A-Class Reorder Count | 57 | Intersection, not A count alone |
| Critical / High / Medium | 23 / 36 / 41 | Total 100; no Routine rows |
| Supplier on-time numerator / denominator | 3,316 / 5,299 | 62.58% when displayed to 2 decimals |
| Supplier receipt rows | 5,299 | Simulated, one per PO |
| Ridge test WAPE / 28-day baseline | ~37.34% / ~37.69% | Confirm test-only measure, pooled absolute errors |

## Relationship and filter tests

- [ ] Confirm every dimension key is unique; no many-to-many or bidirectional link, and no unexpectedly created relationship. Check 100 unique SKU IDs and 1,400 unique SKU×forecast-date pairs.
- [ ] Select one location: sold units, forecast, inventory, ABC and priority counts change; supplier scorecard remains six-supplier global unless supplier is filtered. PO quantity/location context follows SKU→PO.
- [ ] Select one local SKU: current inventory is **one** latest value, ABC and priority have one row, 14 future forecast rows, and 760 historical operation rows. Do not sum the policy threshold across all SKUs.
- [ ] Select one supplier: supplier rate cards, PO/receipt counts and action snapshot cases linked to that supplier change. Historical sales may remain all-SKU because no supplier→SKU relationship was made; label/avoid that mixed-page combination.
- [ ] Date visual check: actual line ends 2024-01-30; forward forecast begins 2024-01-31 and ends 2024-02-13. Month names sort Jan–Dec, year-month sorts chronologically. Calendar covers 2022-01-01–2024-02-13 (774 days).
- [ ] Date slicers do not globally filter the fixed snapshot and are not synchronized across actual and forecast. PO order-date trend uses order dates; receipts are not plotted as if filtered by actual delivery dates.
- [ ] A/B/C, priority and status chart counts each total 100 at full context. Action table has 100 unique SKU rows. No multiplication from joining scorecard and PO or inventory and matrix snapshots.
- [ ] Supplier On-Time % = SUM(on_time_receipts)/SUM(purchase_orders), Fill % = SUM(received_units)/SUM(ordered_units); denominators nonzero, both 0–100%. The score is relative and never summed across suppliers.
- [ ] Clear all slicers before checking global anchors; category, location, SKU, supplier and priority filters intentionally change only reachable measures. Test a single SKU, then clear to restore totals.
- [ ] Supplier page and action page visibly say **SIMULATED**; actual/forecast are visually distinct; recommendations are labeled proposed. No invented screenshots, PBIX, operational savings or realized actions.
- [ ] Save, reopen, refresh and retest anchors. Capture screenshots only from the real Power BI report.

Investigate failures by checking imported numeric types, accidental repeated imports, auto-created relationships, date slicer window, hidden visual filters, and use of a column from the wrong snapshot. The CSV package validation establishes input consistency; it cannot certify Power BI model behavior until these manual checks pass.
