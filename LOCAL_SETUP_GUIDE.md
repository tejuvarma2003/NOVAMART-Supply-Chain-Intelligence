# NOVAMART local setup — Windows PowerShell

This package contains the Phase 1–9 project. The historical source is a published **synthetic** retail dataset ending **2024-01-30**; supplier/PO/receipt records are additional simulations. The forward forecast covers **2024-01-31 through 2024-02-13**. Running the scripts today replays that fixed scenario; it does **not** predict current demand without new data and a new modeling cycle.

## Requirements and first launch

- Windows 10/11; **64-bit Python 3.12** with the Windows `py` launcher; VS Code plus the Microsoft Python extension. Power BI Desktop is needed only to open your existing `.pbix`. SQLite is included with Python, so no separate SQLite server is needed.
- Disk space: allow ~1 GB for an environment, data and regenerated charts; network access is needed for the first package installation. The exact dependencies are pinned in `requirements.txt`. Python 3.12 was used for the validation documented here. Power BI Desktop was not run in this environment.
- Download `NOVAMART_Supply_Chain_Intelligence_Platform_Final.zip` to Downloads. Open **PowerShell** (not Command Prompt). Run these commands **in order**, one line at a time:

```powershell
Expand-Archive -Path "$env:USERPROFILE\Downloads\NOVAMART_Supply_Chain_Intelligence_Platform_Final.zip" -DestinationPath "$env:USERPROFILE\Documents\NOVAMART" 
$ProjectRoot = Join-Path $env:USERPROFILE 'Documents\NOVAMART\SCM_Project'
Set-Location $ProjectRoot
py -3.12 --version
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python src\validate_project.py
python src\predict_with_saved_model.py
```

`Expand-Archive` intentionally has no `-Force`: use a fresh destination so your existing files and `.pbix` are never overwritten. If the `NOVAMART` folder already exists, choose a different **new** destination and update `$ProjectRoot` accordingly. The expected final lines are `"result": "PASS"` and `"status": "PASS"`. If `py -3.12` fails, install 64-bit Python 3.12 with the launcher and reopen PowerShell. The `.venv` stays local and is excluded from the ZIP.

## Open in VS Code

From the same activated terminal:

```powershell
code .
```

If `code` is not on PATH, open VS Code → **File → Open Folder** → choose `Documents\NOVAMART\SCM_Project`. Press **Ctrl+Shift+P** → **Python: Select Interpreter** → `./.venv/Scripts/python.exe`. Open `notebooks/` only after installing dependencies; notebook kernels use the same environment.

## Run validation without changing approved outputs (recommended)

From the project root with `.venv` active:

```powershell
python src\validate_project.py
python src\predict_with_saved_model.py
python src\prepare_phase9.py
```

The first checks SQLite integrity, approved KPIs, and saved model load/inference. The second recomputes all 1,400 forecast rows using the saved model **in memory**, compares them to the approved CSV (six-decimal rounding), and leaves the model/forecast untouched. The third copies unchanged approved CSVs to `dashboard/data/`, derives `date_dim.csv`, and validates keys/counts/hashes. It overwrites **only the dashboard/data copies and dashboard/phase9_validation.json**, so close Power BI before regenerating these CSVs. The approved source/processed data and Ridge artifact are not overwritten by these commands.

For the full reproducibility audit, the following scripts rebuild their respective phase outputs and compare hashes to the included baseline. **Make a separate copy of the project first.** They are useful for troubleshooting, but not needed for normal use:

```powershell
python src\validate_phase3.py
python src\validate_phase4.py
python src\validate_phase5.py
python src\validate_phase6.py
python src\validate_phase7.py
python src\validate_phase8.py
python src\prepare_phase9.py
python src\validate_project.py
```

The Phase 6 validator runs `phase6_forecast.py` and **refits** the candidate models and final Ridge artifact, then proves the approved reports and charts are byte-for-byte unchanged. It does not independently hash-check the binary `.joblib` file; if you must preserve its exact bytes, run only the read-only commands above or back it up first. Refit across package versions may differ. Do not run a validator against a working folder containing new observations you intend to keep unchanged.

## Data and SQLite

- `data/raw/atomicd_retail_inventory_v8.zip` is the original public synthetic dataset archive.
- `data/processed/` contains the seven prepared relational CSVs. `src/build_phase3.py` deterministically recreates them from the raw archive using the fixed seed; it overwrites processed CSVs. Normally use the included files.
- `database/novamart_scm.db` is **included and ready to query**. `database/schema.sql` defines constraints; `sql/01`–`06` contain analytical queries. To rebuild SQLite and five SQL report exports **after backing up your project**:

```powershell
python src\run_phase4.py
python src\validate_phase4.py
```

`run_phase4.py` deletes/recreates the DB from the processed CSVs and overwrites selected Phase 4 exports. Foreign-key and integrity checks are in the validator. To inspect the included database without an external SQLite program:

```powershell
python -c "import sqlite3; c=sqlite3.connect('database/novamart_scm.db'); print(c.execute('SELECT COUNT(*), SUM(units_sold) FROM daily_operations').fetchone()); c.close()"
```

Expect `(76000, 6750876)`.

## Forecasting, inventory and supplier pipelines

For normal **read-only forecasting inference**, use `python src\predict_with_saved_model.py`. The approved serialized model is `models/selected_forecaster.joblib`; the forward CSV and holdout metrics are in `reports/`. To intentionally retrain and regenerate the fixed historical scenario on a **separate copy**, use this order:

```powershell
python src\phase5_eda.py
python src\phase6_forecast.py
python src\inventory_optimization.py
python src\abc_supplier_analysis.py
python src\prepare_phase9.py
python src\validate_project.py
```

The forecasting script refits and overwrites the model and forecast. Phase 7 overwrites recommendations using the new forecast and assumed costs/lead times. Phase 8 overwrites ABC, supplier scores and priorities. Phase 9 then recopies outputs for the dashboard. For a complete raw-to-report rebuild on a spare copy, run `build_phase3.py`, `run_phase4.py`, then the sequence above; follow with the six phase validators. **Do not use these fixed-date scripts as a live forecasting system**. A new calendar, validation periods, model training decision and planning assumptions require deliberate redesign and review.

## Power BI — keep your existing `.pbix`

Your manually completed `.pbix` is on your computer and **is not in this ZIP**. Do not copy the packaged dashboard wireframes over your report. The final Power BI input CSVs are all in `SCM_Project\dashboard\data\` (14 tables including `date_dim.csv`). They contain the same approved numbers as the upstream `reports/` and `data/processed/` files. Use these copied inputs, not both copies.

1. Open **your existing** `.pbix` in Power BI Desktop; immediately **File → Save As** a backup with a new filename.
2. **Home → Transform data**. For every CSV query, choose its `Source` step and change `File.Contents("C:\old\path\file.csv")` to the new full path, for example `File.Contents("C:\Users\YourName\Documents\NOVAMART\SCM_Project\dashboard\data\daily_operations.csv")`. In the Power Query formula bar the actual path uses ordinary Windows backslashes inside the quoted string. If the Source step has a file picker, use **Data source settings → Change Source** instead. Update all 14 paths **only if that table is actually imported**; leave your custom DAX and visuals untouched.
3. **Close & Apply** → Home → **Refresh**. If a privacy-level prompt appears, choose the appropriate level for these local CSV files. Confirm column types remain as in `dashboard/POWERBI_BUILD_GUIDE.md`.
4. Clear slicers and compare the cards against `dashboard/POWERBI_VALIDATION_CHECKLIST.md`. A subset selected in a slicer should give different values. Verify the supplier page visibly says **simulated**. Save/reopen your copy after validation.
5. When you rerun the fixed scenario pipeline, close Power BI first, run `python src\prepare_phase9.py` last, reopen your `.pbix`, click **Refresh**, and rerun the checks. Refresh does not update the 2024 forecast to today's date. For future operational data, stop and redesign/retrain with a new holdout and planning date rather than merely refreshing.

If a query uses a custom parameter or folder path instead of a direct CSV Source step, update its path parameter once rather than manually editing every query. The [Phase 9 model](dashboard/POWERBI_MODEL.md), [DAX library](dashboard/DAX_MEASURES.md) and [build guide](dashboard/POWERBI_BUILD_GUIDE.md) describe expected table names and relationships. Your `.pbix` may have its own measures or transformations; validate it before relying on its visual totals.

## Troubleshooting

| Symptom | Action |
| --- | --- |
| `py` or Python 3.12 not found | Install Python 3.12 (64-bit) with launcher; reopen PowerShell; run `py -3.12 --version`. |
| Activation blocked | In that PowerShell session run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`, then `.\.venv\Scripts\Activate.ps1`; or call `.\.venv\Scripts\python.exe` explicitly without activation. |
| `code` not recognized | Open VS Code via Start menu and use File → Open Folder. |
| `ModuleNotFoundError` | Confirm interpreter points to `.venv`; run `python -m pip install -r requirements.txt`. |
| Model load error / version mismatch | Use the pinned requirements and Python 3.12 in a fresh venv. Do not refit just to silence a mismatch; report the exact exception. |
| Missing CSV or Power BI `File not found` | Extract full ZIP, not an individual script; update each Power Query Source path to `dashboard\data`. |
| Validation KPI mismatch | Clear slicers; confirm exact bundled CSVs, date window and SUM vs DISTINCTCOUNT; inspect `reports/REPRODUCIBILITY_REPORT.md`. Do not edit values to force a pass. |
| `database is locked` | Close DB browsers/other Python sessions, then retry. Back up before rebuilding. |
| Power BI shows duplicate values | Check only one copy per table was imported, model uses single-direction links, and one-to-one SKU snapshots are not joined into daily rows; follow the Phase 9 validation checklist. |
| Pip install fails offline | Restore network, update pip, and retry. If package wheels are unavailable for your Python version, use Python 3.12 and the pinned versions; no offline wheel bundle is included. |

If you want to work on the project in Git, initialize a repository yourself after extraction. The `.gitignore` excludes local environments and secrets. No real vendor or operational benefit should be inferred from the simulated scenario.
