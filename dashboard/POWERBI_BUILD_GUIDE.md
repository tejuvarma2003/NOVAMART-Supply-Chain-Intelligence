# Build the NOVAMART Control Tower in Power BI Desktop (Windows)

**Status:** design and imported data are prepared; no `.pbix` or actual Power BI screenshot exists. Follow the five SVG blueprints in `wireframes/`. Their chart areas are placeholders, not plotted observations. Supplier/procurement data is simulated. Read `POWERBI_MODEL.md`, `DAX_MEASURES.md` and the checklist while building.

## 1. Import and type the data

1. Open Power BI Desktop → Blank report. Set canvas to **16:9**; use approximately 1280×720 px. Turn off automatic date/time in Options (Current File → Data Load) if available.
2. Home → Get data → Text/CSV → choose each of the 14 CSV files in `dashboard/data/` (13 upstream copies + `date_dim`). Select **Transform Data** for each or combine in Power Query. Rename each query to its filename without `.csv`. Load each once. Do not import the upstream copies in `reports/` again.
3. In Power Query, set every `_id`, label, status, class, priority, tier and `year_month` to **Text**. Set each `date`, `forecast_date`, `origin_date`, `order_date`, `expected_delivery_date`, `actual_delivery_date`, `snapshot_date` to **Date** (not Date/Time). Set units/counts/month/week/day/lead-time integer fields to Whole number where integral; prices, ratios, forecast, error, safety stock, reorder point, costs and scores to Decimal number. For `potential_slow_moving`, interpret True/False as Boolean if used. Check no conversion error; Close & Apply.
4. Hide technical lineage fields from the report pane only after documenting them. Keep `local_sku_id`, `supplier_id`, `date_dim[date]` available. Turn off automatic relationships in Manage relationships and create **only** the relationships in `POWERBI_MODEL.md`. Verify unique keys on each one side, single filter direction, no unexpected many-to-many. Mark `date_dim` as Date table using `date_dim[date]`; sort `month_name` by `month_number`, `day_of_week_name` by `day_of_week_number`.
5. Create the measures from `DAX_MEASURES.md`, one at a time. Format WAPE/fill/on-time as percentages; model score as a number with one decimal. The 14-day forecast and planning decimals should show two decimal places on cards; recommended physical units are whole numbers. Set **Do not summarize** on local SKU, status and tier fields.
6. Add a narrow footer to every page: `Historical operations: published synthetic source | Forecast/policy: derived | Supplier/procurement: simulated`. On pages 4 and 5 add the stronger simulated-scenario warning shown below. Page headings and all panels should match the SVG blueprints. Use dark navy `#17324D`, light canvas `#F5F7FA`, blue `#2970B2`, amber `#B7791F`, red `#B42332`, green `#247850`. Text >= 11 pt, title ~24 pt, card number ~22 pt; labels and clear legends accompany color.

## 2. Visual field recipes

All field names below refer to the imported tables. “Count rows” can use a dedicated DAX measure or Count of `local_sku_id` in the named **one-row-per-SKU** table. For trend charts, use `date_dim[date]` rather than the generated date hierarchy. Avoid summarizing text axes. In visual-level filters, choose **Top N** only when specified. On historical charts, filter `date_dim[date] <= 2024-01-30`; forecast chart filters `>= 2024-01-31` and `<= 2024-02-13`. A page-wide historical date filter would hide the forecast, so apply filters **to the individual visuals**.

### Page 1: Executive Overview

- Cards (left to right, two rows if necessary): `[Total Units Sold]`, `[14-Day Forecast Units]`, `[Latest Inventory Units]`, `[SKUs Requiring Reorder]`, `[Critical Cases]`, `[Supplier On-Time %]`. Title supplier card `Simulated on-time %` and add tooltip. These are all-time historical, full forecast horizon and current snapshot respectively; label each period.
- Historical line: X `date_dim[date]` continuous, Y `[Total Units Sold]`, visual filter <=2024-01-30. Use monthly or weekly display granularity for readability. Tooltip units and date.
- Inventory status horizontal bar: Y `replenishment_recommendations[inventory_status]`, X Count of `local_sku_id` from same table; label numbers.
- ABC bar: Y `abc_inventory_classification[abc_class]`, X Count of its `local_sku_id`, sort A/B/C; tooltip Sum of `sales_value_proxy_2023` (value proxy, no currency claim).
- Management priority bar: Y `supply_chain_priority_matrix[management_priority]`, X Count of its `local_sku_id`; order Critical/High/Medium via manual sort or custom sort column. No Routine records in this snapshot.
- Location overview matrix: Rows `locations[location_name]`; Values `[Total Units Sold]`, `[Latest Inventory Units]`, `[SKUs Requiring Reorder]`. Do not add supplier score to this matrix; supplier scorecard has no location grain.
- Slicers: location and category via `locations` and `local_skus`; leave supplier card unsliced by location (independent scenario metric). If this is confusing, use a page card subtitle `All simulated suppliers`.

### Page 2: Demand Planning & Forecast

- Two adjacent line charts with clear ACTUAL/HISTORICAL and MODEL FORECAST headers. Actual X `date_dim[date]`, Y `[Total Units Sold]` and historical visual date filter. Forecast X `date_dim[date]`, Y `[14-Day Forecast Units]` and future date filter. Avoid a single connected line that looks like realized history.
- Category clustered bar: Axis `local_skus[category]`, Values `[Total Units Sold]` and `[14-Day Forecast Units]`, two named series with period labels. Location bar analogous with `locations[location_name]`.
- Test-performance cards: `[Forecast MAE]`, `[Forecast WAPE]`, `[Baseline 28-Day WAPE]`. These respect SKU/location selection, unlike a static reference. For unfiltered view explain Ridge 37.34% vs baseline 37.69%; the gain is modest.
- Error by SKU table: `local_skus[local_sku_id]`, `[Forecast MAE]`, `[Forecast WAPE]`, `sku_demand_profile[cv_daily_units]`; sort descending WAPE. CV is historical SKU demand variability, not a model error. A category axis chart of `[Forecast WAPE]` also works; it pools test errors at category grain.
- Slicers: `locations[location_name]`, `local_skus[category]`, `local_skus[local_sku_id]`. Optional historical Date slicer affects both the historical and forecast visual via shared calendar; if used, disable its interaction with forecast and holdout visuals using Format → Edit interactions. Prefer no date slicer until checks pass.

### Page 3: Inventory Health & Replenishment

- Cards: `[Latest Inventory Units]`, `[SKUs Requiring Reorder]`, `[Recommended Order Units]`, `[Average Safety Stock]`, `[Average Reorder Point]`. Title average policy cards explicitly as *per-SKU averages*.
- Status bar: `replenishment_recommendations[inventory_status]` → Count `local_sku_id`.
- Inventory vs threshold clustered bar: Axis `local_skus[local_sku_id]`, Values `current_inventory` and `reorder_point` from replenishment table; apply Top N 10 by `recommended_order_quantity`, sort descending. Label that reorder point is a threshold, not a stock quantity to sum.
- Order quantities bar: Y `local_skus[local_sku_id]`, X Sum `recommended_order_quantity`; Top N 10 by the same quantity. Category/status and location/status stacked bars: axes `local_skus[category]` / `locations[location_name]`; legend `replenishment_recommendations[inventory_status]`; value Count of recommendation local SKU. All slicers use dimensions, so filtering runs toward the fact.
- Action table: `local_skus[local_sku_id]`, `locations[location_name]`, `local_skus[category]`, `replenishment_recommendations[current_inventory]`, `forecast_14d_units`, `safety_stock`, `reorder_point`, `eoq_reference`, `inventory_status`, `recommended_order_quantity`, `recommendation_priority`. Use **Do not summarize** on one-row SKU fields or select min/max rather than Sum for policy columns. Format order qty as whole units. Conditional format status red/amber and quantity data bars; avoid a green recommendation that implies execution.
- Slicers: location, category, local SKU. Add text note `Snapshot: 2024-01-30; proposed orders have not been placed.`

### Page 4: Supplier Performance — Simulated Scenario

- At top, prominent text: **Supplier and procurement records are simulated for portfolio analysis. Scores are relative within this scenario.**
- Cards: `[Purchase Orders]`, `[Supplier On-Time %]`, `[Supplier Fill %]`, `[Average Actual Lead Time]`. Purchase Orders is from PO fact; supplier rates from scorecard aggregate. Under supplier-only filters these reconcile.
- Four horizontal bars by `suppliers[supplier_name]`: `[Supplier On-Time %]`; `[Supplier Fill %]`; `supplier_scorecard[lead_sd_days]` (one row per supplier, choose Max); `[Supplier Score (selected supplier)]`. Use 0–100% percentage axes on on-time/fill where appropriate and separate unit axes for days and score. Do not put score and lead days on the same axis.
- Detail table: supplier name, scorecard `purchase_orders`, `on_time_pct`, `receipt_fill_pct`, `avg_actual_lead_days`, `avg_positive_delay_all_days`, `supplier_score_assumed_weights`, `supplier_tier`. Use **Do not summarize** for numeric row-level columns or Max in supplier context; `%` scorecard columns are 0–100, whereas DAX measures are 0–1. Label them accurately.
- Slicer: supplier name only. Do not add location/category to scorecard rates: those six aggregate rows cannot recompute supplier performance by location/category. If a location-specific procurement view is desired, PO/receipt event measures must be authored and validated separately.

### Page 5: Supply Chain Action Center

- Cards: `[Critical Cases]`, `[High Priority Cases]`, `[A-Class Reorder Count]`, `[Needs Review Supplier Cases]`. For ABC and supplier tier slicers on this page, use `supply_chain_priority_matrix[abc_class]` and `[supplier_tier]`, and for an A reorder **page-only** measure below to honor those same fact-column filters; see note.
- Priority by category stacked bar: Axis `supply_chain_priority_matrix[category]`, Legend `[management_priority]`, Value Count of `[local_sku_id]`. Separate supplier tier vs priority matrix: Rows `supplier_tier`, Columns `management_priority`, Values Count `[local_sku_id]`.
- Main action table from `supply_chain_priority_matrix`: `local_sku_id`, `location_id`, `category`, `abc_class`, `inventory_status`, `current_inventory`, `reorder_point`, `forecast_14d_units`, `recommended_order_quantity`, `supplier_name`, `supplier_tier`, `management_priority`, `management_reason`. Sort Critical first using a custom numeric sort column (Critical=1, High=2, Medium=3) created on this snapshot, then order quantity descending. Numeric columns **Do not summarize** at SKU grain. To show safety stock/EOQ, create calculated columns on priority matrix with `RELATED(replenishment_recommendations[safety_stock])` only if the one-to-one relationship lets it resolve; safer alternative is display those in a SKU drillthrough from the recommendation table.
- Slicers: `supply_chain_priority_matrix[management_priority]`, `[abc_class]`, `[location_id]`, `[category]`, `[supplier_tier]`. These fact-column slicers affect the action table and matrix-derived cards only. Hide or edit interactions with `[A-Class Reorder Count]` if it appears unchanged; for consistent behavior replace that card with this page measure:

```DAX
A Reorder Cases (Action Page) =
CALCULATE(COUNTROWS(supply_chain_priority_matrix),
    supply_chain_priority_matrix[abc_class] = "A",
    supply_chain_priority_matrix[inventory_status] = "REORDER REQUIRED")
```

The page measure responds to other action slicers; the ABC slicer itself will intersect with A, yielding blank/zero for B/C. If you want an A count independent of the selected ABC class, use `REMOVEFILTERS(supply_chain_priority_matrix[abc_class])` inside `CALCULATE`, and label it accordingly. Use page measure for card; main dictionary measure validates 57 globally.

## 3. Interactions, details and final save

7. Build pages in the above order and use `wireframes/01`–`05` for exact panel arrangement. Keep legend and period labels visible, show integer units and two-decimal forecast numbers. Do not fabricate a chart to fill a panel.
8. Format → Edit interactions: dimension slicers filter only reachable facts; do not imply location filters the supplier scorecard. Do not sync a Date slicer to snapshot pages or across actual/forecast windows. Check a single SKU selection returns exactly one row in each snapshot.
9. Add a hidden optional **SKU Detail** drillthrough page: add `local_skus[local_sku_id]` to Drillthrough fields, keep all filters, then charts for historical sold units and 14-day forecast, cards for current inventory, `[Reorder Point (selected SKU)]`, `[Safety Stock (selected SKU)]`, recommendation quantity, and a table with supplier/ABC/priority from priority matrix. Right-click SKU in a main page visual → Drill through → SKU Detail. This is an optional sixth detail page, not a sixth main dashboard area. Add Back button.
10. Add simple tooltips stating grain, date window and lineage. On simulated supplier page put the warning **in the canvas**, not only the tooltip. Use labels and icons/text plus color for risk. Conditional formatting: Critical dark red, High amber, Medium neutral; status red/amber; no implied realized benefit.
11. Run every item in `POWERBI_VALIDATION_CHECKLIST.md` with all slicers cleared; then select one location, SKU, supplier and date range to inspect context behavior. Compare count, sum and denominator against the package JSON. If a card multiplies fivefold or 100-fold, inspect duplicate imports and relationship directions. If a snapshot vanishes on dates, remove an accidental date→snapshot relationship.
12. File → Save As `dashboard/NOVAMART_Control_Tower.pbix` on your Windows machine, reopen, refresh, repeat anchor checks, then capture **actual** screenshots under `images/dashboard/`. Only after that should the README say a PBIX was built and validated. The authored report itself is a manual outstanding step.

Microsoft reference: [relationships](https://learn.microsoft.com/en-us/power-bi/transform-model/desktop-relationships-understand), [drillthrough](https://learn.microsoft.com/en-us/power-bi/create-reports/desktop-drillthrough), [CSV sources](https://learn.microsoft.com/en-us/power-bi/connect-data/desktop-data-sources).
