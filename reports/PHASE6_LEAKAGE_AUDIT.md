# Phase 6 feature availability and leakage audit

Forecast origin = latest observed date at a 14-day decision point. The model predicts each of the next 14 days directly using **one frozen history** at that origin. Validation/test blocks do not overlap within a split. Their next origin may use sales that have become historically available since the prior block. No row uses actual sales from its own forecast window as a feature.

| Feature | Origin | Known at forecast issue? | Main model? | Reason |
| --- | --- | --- | --- | --- |
| `last_sales`, `lag_7`, `lag_14`, `lag_28` | `units_sold` at origin / 7th / 14th / 28th most recent observed dates | Yes | Yes | All from the 28 observed days ending at origin; not future target rows. |
| `mean_7`, `mean_14`, `mean_28` | Mean of last 7/14/28 observed sales | Yes | Yes | Constructed from `history.loc[:origin]`; forecast window excluded. |
| `std_7`, `std_28` | Population SD of last 7/28 observed sales | Yes | Yes | Same cutoff. |
| `horizon_day` | Planned 1–14 day-ahead offset | Yes | Yes | Defines which day is predicted directly. |
| `target_dow`, `target_month`, `target_weekend` | Future calendar date | Yes | Yes | Deterministic calendar; no realized future data. |
| `local_sku_id`, `location_id`, `category` | Approved stable identity/dimension | Yes | Yes | Product is local to store; one-hot encoded in Ridge. |
| Same-day/future `units_sold` | Realized target | No | No | Direct target leakage. |
| Publisher `estimated_demand_source` | Synthetic publisher estimate | Availability and construction unclear | No | Not verified demand; 21,000 days below sales; high risk of target contamination. |
| Future `inventory_units` / `units_ordered_source` | Realized source snapshots | No | No | Post-decision operational information. |
| Price, discount, promotion | Source daily realized fields | Future plans not supplied | No | Cannot assume the 14-day values were known at issue time. |
| Weather, competitor pricing, epidemic flag | Source daily realized fields | Future actuals unknown | No | Would require genuine as-of forecasts/plans. |
| Simulated supplier delivery or receipt | Scenario outcome | No | No | Future outcome and separate lineage. |

The validator perturbs **all sales after an origin** and confirms every training feature at that origin remains byte-equivalent. It also hand-checks the 7th and 28th historical values and 28-day mean. Validation is chosen without consulting the test set; the final model is refit after the holdout for forward predictions. Source itself is synthetic.
