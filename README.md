
# NOVAMART — Supply Chain Intelligence Platform

**End-to-end supply chain analytics portfolio project | Python · SQL · Machine Learning · Power BI**

NOVAMART is a fictional five-location retail operation. This project transforms a **published synthetic retail dataset** into a reproducible analytics workflow covering data quality, relational SQL analysis, exploratory analysis, 14-day sales forecasting, scenario-based inventory planning, ABC classification, simulated supplier scoring, and an interactive five-page Power BI Supply Chain Control Tower.

**Project status:** Phases 1–9 analytics and dashboard preparation are complete. A five-page Power BI report was built, checked, and saved separately on Windows as `NOVAMART_Supply_Chain_Control_Tower_Local_Final.pbix`. The `.pbix` is not included in the supplied project archive. GitHub and portfolio packaging is the remaining step.

> **Data provenance:** The retail observations are synthetic, not transactions from a real business. Supplier records, purchase orders, and receipts are additional simulated scenarios. Forecasts, inventory recommendations, and supplier scores are analytical outputs, not live decisions, executed purchases, or measured financial benefits.

## Project Highlights

| Metric | Result | Interpretation |
| --- | ---: | --- |
| Historical daily observations | 76,000 | 100 local SKUs × 760 days, Jan 2022–Jan 2024 |
| Locations / local SKUs | 5 / 100 | Each product identifier is store-specific |
| Historical units sold | 6,750,876 | Published synthetic fulfilled sales |
| Selected forecast model | Ridge Regression | Selected using validation and a predefined simplicity rule |
| Test WAPE | 37.34% | Compared with 37.69% for the 28-day average baseline |
| Forward forecast | 126,137.36 units | 1,400 predictions for Jan 31–Feb 13, 2024 |
| Latest recorded inventory | 29,049 units | Historical snapshot dated Jan 30, 2024 |
| Reorder-review cases | 97 of 100 | Under documented inventory-policy assumptions |
| Proposed replenishment | 180,766 units | Proposed quantities, not issued purchase orders |
| Management priorities | 23 Critical / 36 High / 41 Medium | Rule-based review queue |

## Business Problem

Retail supply chains face challenges in balancing product availability, demand variability, supplier reliability, and inventory costs.

NOVAMART addresses the following questions:

- What are historical sales and inventory patterns by store, category, and SKU?
- How accurately can future sales be forecast using historical data?
- Which store-specific products trigger replenishment review?
- Which high-value SKUs require greater management attention?
- How do simulated supplier delivery patterns affect operational risk?
- How can supply chain managers monitor and prioritize these issues through Power BI?

The objective is to develop an analytical decision-support system that connects historical data, forecasting, inventory planning, and management reporting.

## Analytical Workflow

```text
Published Synthetic Retail Dataset
        |
        v
Data Profiling and Quality Validation
        |
        v
ERP-Style Relational Data Preparation
        |
        v
SQLite Database and SQL Analysis
        |
        v
Exploratory Data Analysis
        |
        v
14-Day Demand Forecasting
        |
        v
Inventory Replenishment Scenario
        |
        v
ABC Classification and Supplier Scoring
        |
        v
Management Priority Matrix
        |
        v
Power BI Supply Chain Control Tower
```

## Phase 1 — Business Problem and Project Definition

Defined the fictional retail business scenario, operational decision requirements, stakeholders, project scope, and analytical objectives.

The primary decision unit is a **local SKU**, representing a product at a specific store.

The project is an ERP-style analytics simulation, not an SAP implementation or production ERP system.

## Phase 2 — Dataset Selection and Data Quality

Selected a published synthetic retail inventory and demand dataset containing:

- 5 retail locations
- 100 store-specific local SKUs
- 760 daily observations per SKU
- 76,000 historical daily records
- Dates from January 1, 2022, through January 30, 2024

Performed data profiling, identifier validation, and source-quality checks.

The original product identifiers were not globally unique across stores, so store-specific local SKU identifiers were created.

**Documentation:**

- [Dataset Quality Report](reports/PHASE2_DATA_QUALITY.md)

## Phase 3 — ERP-Style Data Preparation

Developed a relational data structure containing seven tables:

1. Locations
2. Local SKUs
3. Daily Operations
4. Suppliers
5. SKU–Supplier Mapping
6. Purchase Orders
7. Receipts

The supplier, purchase-order, and receipt tables are additional simulated procurement scenarios.

The simulated procurement records are not reconciled with the original retail inventory snapshots.

**Documentation:**

- [ERP Data Preparation Report](reports/PHASE3_ERP_DATA_PREPARATION.md)

## Phase 4 — SQL Supply Chain Analysis

Built a SQLite database and developed six SQL analysis files covering:

- Data integrity and validation
- Sales and demand analysis
- Inventory analysis
- Simulated procurement analysis
- Simulated supplier performance
- Supply chain management exceptions

SQL techniques include:

- Joins
- Common Table Expressions (CTEs)
- Window functions
- Conditional aggregation
- Date calculations
- Grouping and aggregation

**Documentation:**

- [SQL Analysis Report](reports/PHASE4_SQL_ANALYSIS.md)
- [SQL KPI Dictionary](reports/SQL_KPI_DICTIONARY.md)

## Phase 5 — Exploratory Data Analysis

Used Python to examine:

- Sales trends by location and category
- SKU-level sales variability
- Historical inventory availability
- Inventory coverage
- Promotion and pricing associations
- Simulated supplier delivery outcomes

### Selected Findings

- Total historical units sold: **6,750,876**
- Zero-inventory SKU-days: **406**
- Median latest inventory coverage: approximately **2.824 days**, using a historical 28-day sales proxy
- SKUs below the descriptive seven-day coverage screen: **90 of 100**

Promotional associations were examined descriptively and are not interpreted as causal effects.

**Documentation:**

- [EDA Report](reports/PHASE5_EDA_ANALYSIS.md)

Visualizations are available in `images/eda/`.

## Phase 6 — Demand Forecasting

Developed a 14-day sales forecasting workflow using historical SKU-level observations.

### Models Evaluated

- Last-observation baseline
- 7-day moving-average baseline
- 28-day moving-average baseline
- Ridge Regression
- Histogram Gradient Boosting

Used chronological training, validation, and test periods to reduce the risk of future-data leakage.

Ridge Regression was selected using validation performance and a predefined model-simplicity rule before evaluating the untouched test set.

### Forecasting Results

| Metric | Ridge Regression |
| --- | ---: |
| Test MAE | 32.56 |
| Test RMSE | 41.17 |
| Test WAPE | 37.34% |
| 28-day baseline test WAPE | 37.69% |

The improvement over the strongest simple baseline was modest: **0.35 percentage points in WAPE**.

The final model generated:

- 1,400 daily SKU-level predictions
- 100 local SKUs
- 14-day forecast horizon
- Forecast dates: January 31–February 13, 2024
- Total forecast: **126,137.36 units**

These forecasts represent a fixed historical scenario, not current demand predictions.

**Documentation:**

- [Demand Forecasting Report](reports/PHASE6_DEMAND_FORECASTING.md)
- [Forecast Leakage Audit](reports/PHASE6_LEAKAGE_AUDIT.md)

## Phase 7 — Inventory Optimization and Replenishment

Developed a scenario-based inventory planning framework using:

- Forecast daily sales
- Historical forecast-error variation
- Latest historical inventory snapshots
- Simulated supplier lead times
- Assumed inventory-policy parameters

### Inventory Calculations

**Safety Stock**

```text
Safety Stock = 1.645 × Forecast Error SD × sqrt(Lead Time)
```

**Reorder Point**

```text
Reorder Point = Forecast Daily Sales × Lead Time + Safety Stock
```

**Target Stock**

```text
Target Stock = Forecast Daily Sales × (Lead Time + 14) + Safety Stock
```

**Proposed Order Quantity**

For SKUs at or below the reorder point:

```text
Proposed Order = ceil(max(0, Target Stock - Current Inventory))
```

Economic Order Quantity (EOQ) was also calculated as a separate reference using assumed ordering and holding costs.

### Results

| Metric | Result |
| --- | ---: |
| Local SKUs evaluated | 100 |
| Reorder Required | 97 |
| Low Stock / At Risk | 3 |
| Proposed replenishment units | 180,766 |
| Mean safety stock | 175.48 units |
| Mean EOQ reference | 891.53 units |

These results are scenario-based planning recommendations, not executed orders or verified financial savings.

**Documentation:**

- [Inventory Optimization Report](reports/PHASE7_INVENTORY_OPTIMIZATION.md)
- [Inventory Assumptions](reports/INVENTORY_ASSUMPTIONS.md)

## Phase 8 — ABC Inventory and Simulated Supplier Performance

### ABC Inventory Classification

Classified 100 local SKUs using complete-year 2023 historical sales-value proxies.

```text
Sales Value Proxy = SUM(Units Sold × Listed Price)
```

| ABC Class | Local SKUs | Share of Sales-Value Proxy |
| --- | ---: | ---: |
| A | 60 | 80.881% |
| B | 24 | 14.505% |
| C | 16 | 4.614% |

This is a synthetic historical sales-value proxy, not audited revenue or profit.

### Simulated Supplier Performance

Evaluated six simulated suppliers using:

- On-time delivery: 40%
- Order fill rate: 30%
- Lead-time consistency: 20%
- Delivery delay: 10%

Supplier scores are relative to the six simulated suppliers and use assumed weights.

### Management Priority Matrix

Combined ABC class, inventory status, and supplier performance tier to identify management-review priorities.

| Management Priority | Local SKUs |
| --- | ---: |
| Critical | 23 |
| High | 36 |
| Medium | 41 |
| Routine | 0 |

These are analytical review classifications, not confirmed operational incidents.

**Documentation:**

- [ABC and Supplier Analysis Report](reports/PHASE8_ABC_SUPPLIER_ANALYSIS.md)

## Phase 9 — Power BI Supply Chain Control Tower

Developed a five-page Power BI dashboard to support supply chain monitoring, forecasting, inventory review, supplier evaluation, and management prioritization.

The report was built, checked, and saved separately in Power BI Desktop on Windows.

**Local Power BI filename:**

`NOVAMART_Supply_Chain_Control_Tower_Local_Final.pbix`

The original project archive contains the dashboard-ready data and documentation. The separately saved `.pbix` should be added to the publication package only after confirming its contents and file size.

### Dashboard Pages

| Page | Purpose |
| --- | --- |
| Executive Overview | Monitor historical sales, forecast demand, inventory, and exceptions |
| Demand Planning | Analyze historical sales, forward forecasts, and forecast reliability |
| Inventory & Replenishment | Review inventory coverage, reorder points, and proposed order quantities |
| Supplier Performance — Simulated Scenario | Analyze simulated supplier delivery and scorecard metrics |
| Supply Chain Action Center | Prioritize SKU-level management review cases |

### Power BI Features

- Interactive slicers
- KPI cards
- Historical sales and forecast visualizations
- Inventory and replenishment analysis
- Simulated supplier performance reporting
- Management-priority filtering
- Relational data modeling and DAX measures

Actual dashboard screenshots should be added before publishing the repository.

**Documentation:**

- [Power BI Data Model](dashboard/POWERBI_MODEL.md)
- [DAX Measures](dashboard/DAX_MEASURES.md)
- [Power BI Build Guide](dashboard/POWERBI_BUILD_GUIDE.md)
- [Power BI Validation Checklist](dashboard/POWERBI_VALIDATION_CHECKLIST.md)
- [Phase 9 Report](reports/PHASE9_POWERBI_CONTROL_TOWER.md)

## Technology Stack

| Category | Technologies |
| --- | --- |
| Programming | Python |
| Data Processing | pandas, NumPy |
| Database | SQLite |
| Querying | SQL |
| Machine Learning | scikit-learn |
| Data Visualization | Matplotlib |
| Business Intelligence | Power BI Desktop |
| BI Calculations | DAX |
| Development | VS Code, Jupyter Notebooks |
| Version Control | Git, GitHub |

## Repository Structure

```text
SCM_Project/
├── README.md
├── requirements.txt
├── LOCAL_SETUP_GUIDE.md
├── data/
│   ├── raw/
│   └── processed/
├── database/
├── sql/
├── notebooks/
├── src/
├── models/
├── dashboard/
│   ├── data/
│   ├── wireframes/
│   ├── POWERBI_MODEL.md
│   ├── DAX_MEASURES.md
│   └── POWERBI_BUILD_GUIDE.md
├── reports/
└── images/
    ├── eda/
    ├── inventory/
    └── abc_supplier/
```

## Running the Project Locally

The project was tested using Python 3.12 on Windows.

Follow [LOCAL_SETUP_GUIDE.md](LOCAL_SETUP_GUIDE.md) for full environment setup and Power BI file-path configuration.

After activating the Python environment and installing dependencies, run the following commands from the project root:

```powershell
python src\validate_project.py
python src\predict_with_saved_model.py
```

The first command validates the approved project outputs.

The second loads the saved Ridge forecasting model and performs inference without retraining.

The forecast is based on the historical dataset ending January 30, 2024. Running the script does not create a live forecast for today's date.

For tested commands and limitations, see:

- [Reproducibility Report](reports/REPRODUCIBILITY_REPORT.md)

## Project Limitations

This project is designed as an analytical portfolio case study.

Important limitations include:

1. **Synthetic retail data:** The original dataset contains publisher-generated synthetic observations rather than actual retail transactions.

2. **Simulated procurement:** Supplier records, purchase orders, and receipts were additionally simulated and do not reconcile with the original source inventory movements.

3. **Observed sales versus demand:** Forecasts predict recorded `units_sold`, not verified unconstrained customer demand.

4. **Historical inventory:** The latest stock values represent January 30, 2024, rather than real-time inventory.

5. **Inventory assumptions:** Lead times, service targets, ordering costs, holding rates, and safety-stock assumptions are scenario parameters.

6. **Supplier scoring:** Supplier rankings are relative scores across six simulated suppliers, not externally validated vendor assessments.

7. **No realized savings:** Replenishment recommendations were not executed, and the project does not claim measured financial or operational improvements.

## Project Status

**Completed:**

- Business problem definition
- Dataset selection and validation
- ERP-style relational data preparation
- SQL supply chain analysis
- Exploratory data analysis
- Demand forecasting
- Inventory replenishment scenario
- ABC classification and supplier scoring
- Power BI-ready data preparation
- Five-page Power BI dashboard built on Windows

**Final publishing tasks:**

- Update Phase 9 documentation to reflect the completed local dashboard
- Add actual Power BI screenshots
- Review repository files before publication
- Publish the GitHub repository
- Prepare the portfolio case study

---

**NOVAMART Supply Chain Intelligence Platform** demonstrates an end-to-end analytical workflow connecting historical retail data, machine learning, inventory planning, simulated procurement analysis, and business intelligence reporting.

*This is a portfolio project, not a live ERP system or production supply chain application.*
