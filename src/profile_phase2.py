"""Read the original Kaggle archive and report Phase 2 data quality; no data mutation."""
import hashlib
import json
import zipfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "data/raw/atomicd_retail_inventory_v8.zip"
OUTPUT = ROOT / "reports/phase2_profile.json"


def summary(s):
    x = pd.to_numeric(s, errors="coerce")
    return {"min": float(x.min()), "p05": float(x.quantile(.05)),
            "p25": float(x.quantile(.25)), "median": float(x.median()),
            "mean": float(x.mean()), "p75": float(x.quantile(.75)),
            "p95": float(x.quantile(.95)), "max": float(x.max()),
            "zero_count": int(x.eq(0).sum()), "negative_count": int(x.lt(0).sum())}


def main():
    with zipfile.ZipFile(ARCHIVE) as z:
        assert z.namelist() == ["sales_data.csv"]
        with z.open("sales_data.csv") as f:
            df = pd.read_csv(f)
    dates = pd.to_datetime(df["Date"], errors="coerce")
    key = ["Date", "Store ID", "Product ID"]
    series = df.groupby(["Store ID", "Product ID"])["Date"].nunique()
    full_days = len(pd.date_range(dates.min(), dates.max()))
    categorical = ["Category", "Region", "Weather Condition", "Seasonality", "Promotion", "Epidemic", "Discount"]
    numeric = ["Inventory Level", "Units Sold", "Units Ordered", "Demand", "Price", "Discount", "Competitor Pricing"]
    out = {
        "source": "https://www.kaggle.com/datasets/atomicd/retail-store-inventory-and-demand-forecasting",
        "archive_sha256": hashlib.sha256(ARCHIVE.read_bytes()).hexdigest(),
        "shape": list(df.shape), "columns": list(df.columns),
        "dtypes": {k: str(v) for k,v in df.dtypes.items()},
        "date_parse_failures": int(dates.isna().sum()),
        "date_min": str(dates.min().date()), "date_max": str(dates.max().date()),
        "calendar_days": full_days, "observed_days": int(dates.nunique()),
        "rows_per_day": summary(df.groupby("Date").size()),
        "stores": int(df["Store ID"].nunique()), "products": int(df["Product ID"].nunique()),
        "store_product_pairs": int(series.size), "series_length_days": summary(series),
        "expected_complete_grid_rows": int(series.size * full_days),
        "missing_grid_rows": int(series.size * full_days - len(df.drop_duplicates(key))),
        "missing_values": {k:int(v) for k,v in df.isna().sum().items()},
        "exact_duplicates": int(df.duplicated().sum()), "duplicate_grain_keys": int(df.duplicated(key).sum()),
        "categorical_counts": {k:{str(a):int(b) for a,b in df[k].value_counts(dropna=False).items()} for k in categorical},
        "numeric_summary": {k:summary(df[k]) for k in numeric},
        "invalid_flags": {k:int((~df[k].isin([0,1])).sum()) for k in ["Promotion","Epidemic"]},
        "discount_outside_0_100": int((~df["Discount"].between(0,100)).sum()),
        "sold_exceeds_inventory": int((df["Units Sold"] > df["Inventory Level"]).sum()),
        "sold_exceeds_demand": int((df["Units Sold"] > df["Demand"]).sum()),
        "demand_below_sold": int((df["Demand"] < df["Units Sold"]).sum()),
        "zero_inventory_positive_sales": int(((df["Inventory Level"] == 0) & (df["Units Sold"] > 0)).sum()),
        "product_category_conflicts": int(df.groupby("Product ID")["Category"].nunique().gt(1).sum()),
        "store_region_conflicts": int(df.groupby("Store ID")["Region"].nunique().gt(1).sum()),
        "weekday_demand_mean": {str(k):round(float(v),2) for k,v in df.groupby(dates.dt.day_name())["Demand"].mean().items()},
        "monthly_demand_mean": {str(k):round(float(v),2) for k,v in df.groupby(dates.dt.to_period("M"))["Demand"].mean().items()},
        "seasonality_calendar_conflicts": int((df["Seasonality"] != dates.dt.month.map({12:"Winter",1:"Winter",2:"Winter",3:"Spring",4:"Spring",5:"Spring",6:"Summer",7:"Summer",8:"Summer",9:"Autumn",10:"Autumn",11:"Autumn"})).sum()),
        "distinct_prices_by_product_median": float(df.groupby("Product ID")["Price"].nunique().median()),
        "distinct_inventory_per_pair_median": float(df.groupby(["Store ID","Product ID"])["Inventory Level"].nunique().median()),
    }
    OUTPUT.write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({k:out[k] for k in ["shape","date_min","date_max","calendar_days","stores","products","store_product_pairs","missing_grid_rows","exact_duplicates","duplicate_grain_keys","product_category_conflicts","store_region_conflicts","sold_exceeds_inventory","sold_exceeds_demand","seasonality_calendar_conflicts"]},indent=2))


if __name__ == "__main__":
    main()
