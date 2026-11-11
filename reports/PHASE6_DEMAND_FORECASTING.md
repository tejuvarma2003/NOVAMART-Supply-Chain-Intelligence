# Phase 6 — demand forecasting and machine learning

## Business question and target

Predict daily fulfilled `units_sold` for each of 100 **store-specific local SKUs** over the next **14 days**. These forecasts will be inputs to later inventory scenarios; they are not replenishment orders, real-world production forecasts, or verified unconstrained customer demand. The public source itself is synthetic and observed sales may be stock constrained. Publisher-estimated `Demand` is excluded.

This is time-series forecasting because future days must be predicted from an earlier decision date. A random row split would give a model later dates and overlapping histories during training and overstate performance.

## Chronological design and multi-step method

| Set | Forecast-origin dates | Target dates | Rows |
| --- | --- | --- | ---: |
| Training | Every 14 days, 2022-01-28–2023-08-11 | 2022-01-29–2023-08-25 | 57,400 |
| Validation | 2023-09-01, 09-15, 09-29, 10-13, 10-27 | 2023-09-02–2023-11-10 | 7,000 |
| Untouched test | 2023-11-11, 11-25, 12-09, 12-23, 2024-01-06 | 2023-11-12–2024-01-20 | 7,000 |

The remaining observations through **2024-01-30** are available for final refitting and forecast issuance. Every local SKU shares cutoffs. Each origin creates 14 direct horizon rows using **the same 28-day history ending on the origin date**, calendar for the particular target date, and static identity. The model predicts day 1 through day 14 without inserting actual future sales into any lag. At a later backtest origin, intervening realized sales are legitimately historical as of that later decision. There is a deliberate gap after training targets and before validation targets.

Global models pool all 100 series. Ridge one-hot encodes local SKU, location, category and scales numeric inputs; HistGradientBoosting uses fixed categorical codes for the same identifiers. Separate complex models for each SKU would be unnecessary at this project scale. Features and explicit exclusions are in [PHASE6_LEAKAGE_AUDIT.md](PHASE6_LEAKAGE_AUDIT.md). No future price, promotion, weather, inventory, estimated demand, or simulated delivery outcome enters the main model.

## Models, metrics, and decision

Baselines predict every day in the block with the last observed sales, the preceding 7-day average, or preceding 28-day average. Ridge and HistGradientBoosting each predict daily horizon values directly. Negative outputs are clipped to zero. MAE = mean absolute daily-unit error; RMSE = square root of mean squared daily-unit error; WAPE = 100 × sum absolute error / sum actual units. Global denominators are positive. MAPE was omitted because some source sales are zero and individual percentage errors would be undefined or unstable.

| Split | Method | MAE units/day | RMSE units/day | WAPE |
| --- | --- | ---: | ---: | ---: |
| Validation | Last observed | 39.59 | 51.03 | 47.47% |
| Validation | 7-day mean | 31.40 | 40.69 | 37.65% |
| Validation | 28-day mean | 32.18 | 40.50 | 38.59% |
| Validation | Ridge | 30.36 | 38.44 | 36.40% |
| Validation | HistGradientBoosting | 29.76 | 37.87 | 35.68% |
| Test | Last observed | 42.94 | 54.52 | 49.25% |
| Test | 7-day mean | 35.52 | 44.92 | 40.74% |
| Test | 28-day mean | 32.86 | 41.80 | 37.69% |
| Test | **Ridge (selected)** | **32.56** | **41.17** | **37.34%** |
| Test | HistGradientBoosting | 32.67 | 41.39 | 37.47% |

Selection uses validation WAPE and a declared parsimony rule: choose Ridge if it is within **one percentage point** of the best validation result. It trailed the nonlinear candidate by 0.72 points, so Ridge was chosen before examining the test. On the test, Ridge improved WAPE by **0.35 percentage points** (about **0.93% relative**) against the strongest simple 28-day baseline. This is a modest gain; the simpler moving average remains a credible fallback. Against last-observation naive it improved WAPE by **11.91 points**, though the stronger mean baseline is the fairer comparison. No claim of business improvement is made.

## SKU and segment diagnostics

The separate `forecast_error_by_sku.csv` combines **validation and test out-of-sample predictions** (140 daily rows per SKU) and provides MAE, RMSE, residual population SD, and WAPE. It is historical error information for Phase 7, **not** a formal prediction interval. Best SKU WAPE is `S004_P0019` **26.26%**; worst is `S005_P0016` **50.04%**. The median SKU WAPE is **37.74%**. Poor series are retained, not hidden.

Test WAPE by category: Clothing **30.97%**, Groceries **36.63%**, Electronics **38.16%**, Furniture **41.27%**, Toys **44.75%**. Test location WAPE ranges from **36.62% (`S003`) to 38.00% (`S005`)**. WAPE can be higher for lower-volume segments even when MAE is lower. See the error-versus-SKU-variability figure for exploratory comparison; neither the coefficients nor model features imply causation.

## Forward forecast and interpretation

After holdout evaluation, Ridge was refit using eligible historical training windows through the available source end date **2024-01-30** and predicts **2024-01-31–2024-02-13**. `demand_forecast_14d.csv` has **1,400 rows**: 100 local SKUs × 14 future dates, all nonnegative, totaling **126,137.36 predicted units** before any whole-unit rounding. `demand_forecast_14d_summary.csv` has one row per SKU with a 14-day sum and daily mean; the SKU sums range about **849.08–1,662.21** units. Values remain fractional model expectations; later order quantities must apply explicit rounding and inventory policy, not silently round these daily estimates.

The Ridge model is in `models/selected_forecaster.joblib`. Its standardized numeric coefficients are largest in magnitude for overlapping 7/14/28-day means; these are correlated historical summaries, so individual coefficient signs should not be treated as independent causal importance. Calendar and identity terms aid pooled prediction but do not prove effects.

## Files, validation, and limitations

Pipeline `src/phase6_forecast.py`; validator `src/validate_phase6.py`; notebook `notebooks/02_demand_forecasting.ipynb`; feature audit above; reports include model comparison, holdout predictions, SKU error summary, category/location summaries, forward daily and aggregate forecasts, and run manifest. Five charts under `images/forecasting/` show model comparison, representative test sequence, category WAPE, error versus historical SKU variability, and forward example.

Validation passed chronological bounds, complete 100 × 14 future grid, nonnegative forecasts, recomputed MAE/RMSE/WAPE for every candidate and split, hand-checked lags, perturbed future targets to check feature invariance, and reproduced all report/chart hashes. The public source is synthetic, its sales may be censored by stock, the holdout covers five 14-day decisions, only about two years of annual history exist, and the 14-day horizon remains a provisional business policy. Performance may differ on real operations or other seasons. Phase 7 optimization has not started.
