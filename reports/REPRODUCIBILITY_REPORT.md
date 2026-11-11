# NOVAMART final local-package validation

**Scope:** recovered Phase 9 project archive, inspected the project tree, executed validations with Python **3.12.14** (pandas 2.2.3, NumPy 2.3.5, matplotlib 3.10.8, scikit-learn 1.8.0, joblib 1.5.3), then packaged the verified project. The analysis concerns a **fixed 2022–2024 synthetic-data scenario**, not a current operational feed. No local Windows Power BI report was accessed.

## Executed checks

| Executed command | Result | What it actually checked |
| --- | --- | --- |
| `python src/profile_phase2.py` | PASS; output hash unchanged | Raw 76,000-row dataset shape, date panel, dictionary source profile; synthetic source quality |
| `python src/validate_phase3.py` | PASS | Seven tables, keys, coverage, foreign references, lineage, deterministic rebuild hashes |
| `python src/validate_phase4.py` | PASS | SQLite integrity/FKs, joins, dates, spend arithmetic, SQL export reproducibility |
| `python src/validate_phase5.py` | PASS | SQL-to-EDA reconciliation and nine visual/export hashes |
| `python src/validate_phase6.py` | PASS | Chronological holdouts, 14-day features, baseline/model metrics, report/chart hashes; internally refitted Ridge |
| `python src/validate_phase7.py` | PASS | Forecast-to-policy joins, formulas, labels, physical order rounding, reproducibility |
| `python src/validate_phase8.py` | PASS | ABC value reconciliation, supplier scores/weights, priorities, joins, reproducibility |
| `python src/predict_with_saved_model.py` | PASS | Existing `.joblib` loaded; all 1,400 in-memory predictions match approved six-decimal CSV |
| `python src/validate_project.py` | PASS | Read-only SQLite, model inference and nine requested anchor families |
| `python src/prepare_phase9.py` | PASS | Upstream CSV byte identity, 14 dashboard CSV tables, relationship keys, anchors |
| `python -m compileall` / ZIP CRC | PASS | All source syntax / all package entries decompress cleanly |

The Phase 6 validator refitted the model as part of its reproducibility check. Its resulting `.joblib` **SHA-256 matched the Phase 9 archive exactly** (`b3c156bf726831ac3969cb8daa87233450d61f9b9700f74e10cb67802d14d5f5`); the approved forecast CSV and processed daily input hashes also matched. The new read-only inference script does not retrain or write forecast/model files. No forecast, inventory, ABC or supplier results were intentionally changed.

## Approved anchor reconciliation

| Metric | Recomputed result | Source |
| --- | ---: | --- |
| Historical units sold | 6,750,876 | SQLite `daily_operations` |
| 14-day forecast units | 126,137.36 | `demand_forecast_14d.csv` |
| Latest inventory | 29,049 | `replenishment_recommendations.csv` source snapshot field |
| Reorder cases | 97 | Recommendation status |
| Proposed order units | 180,766 | Recommendation quantity |
| ABC classes | A 60, B 24, C 16 | 2023 sales-value proxy |
| Management priority | Critical 23, High 36, Medium 41 | Derived action snapshot |
| Simulated on-time delivery | 3,316 / 5,299 = 62.58% | PO/receipt dates in SQLite |
| Ridge test WAPE | 37.34% | `forecast_model_comparison.csv` test split |

All values reconcile to prior phase outputs. These are historical/scenario anchors, **not today's KPIs**. Phase 9 `date_dim` spans 2022-01-01–2024-02-13. Forecast holds 100 local SKUs × 14 days.

## Artifacts and exclusions

The ZIP includes `SCM_Project/` with original raw archive, seven processed CSVs, SQLite DB/schema, six SQL files, four notebooks, selected Ridge model, source and validators, reports/data dictionary, charts, and 14 dashboard CSVs plus wireframes and DAX/model/build guidance. The upstream CSVs are duplicated under `dashboard/data/` **by design**: the dashboard folder is a stable import boundary, and the Phase 9 script verifies identical hashes. Phase-specific analysis exports and charts are distinct deliverables, not obsolete development copies. Empty `.gitkeep` files may be omitted from the final ZIP. No `.venv`, cache, credential, or user's private `.pbix` is included.

## Limits and unresolved local checks

- **Windows install/VS Code/Power BI refresh not executed here.** The tests ran on Linux with Python 3.12.14 and the pinned runtime dependencies. `ipykernel` was not installed in the test runtime, so notebook kernels were not executed; the equivalent Python source pipelines and validators were executed. A fresh `pip install -r requirements.txt` was not performed in a Windows venv.
- The user's five-page `.pbix` exists only on their Windows computer. Its data-source paths, DAX, visual values and refresh were not inspectable or validated. Follow `LOCAL_SETUP_GUIDE.md` and `dashboard/POWERBI_VALIDATION_CHECKLIST.md` against the actual report.
- The source dataset is published synthetic data; suppliers, purchase orders and receipts are simulated; ABC value is a 2023 sales-value proxy; recommendations are proposed, not implemented. The project does not claim real supplier performance or savings.
- The scripts' origin dates and forecast horizon are fixed to the historical panel. New live data would require updating assumptions, split dates, feature handling, model evaluation, and the forecast origin before any production use.
- `requirements.txt` uses exact pins. On another Python/OS build, model serialization may require identical compatible versions; diagnose errors before retraining. The package contains no offline wheel cache.
