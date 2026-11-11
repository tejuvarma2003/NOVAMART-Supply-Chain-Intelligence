"""Package unchanged Phase 3–8 CSVs for Power BI and verify reporting anchors."""
import csv
import hashlib
import json
import shutil
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "dashboard" / "data"
FILES = {
    "locations": "data/processed", "local_skus": "data/processed",
    "daily_operations": "data/processed", "suppliers": "data/processed",
    "purchase_orders": "data/processed", "receipts": "data/processed",
    "demand_forecast_14d": "reports", "forecast_holdout_predictions": "reports",
    "replenishment_recommendations": "reports", "abc_inventory_classification": "reports",
    "supplier_scorecard": "reports", "supply_chain_priority_matrix": "reports",
    "sku_demand_profile": "reports",
}


def rows(name):
    with (OUT / f"{name}.csv").open(newline="") as stream:
        yield from csv.DictReader(stream)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for name, folder in FILES.items():
        src = ROOT / folder / f"{name}.csv"
        dst = OUT / src.name
        shutil.copyfile(src, dst)
        assert digest(src) == digest(dst), name
        manifest[name] = {"rows": sum(1 for _ in rows(name)), "sha256": digest(dst), "upstream": str(src.relative_to(ROOT))}
    dates = []
    for name, cols in {"daily_operations": ["date"], "demand_forecast_14d": ["forecast_date"],
                       "purchase_orders": ["order_date", "expected_delivery_date"],
                       "receipts": ["actual_delivery_date"],
                       "forecast_holdout_predictions": ["origin_date", "forecast_date"]}.items():
        for r in rows(name):
            dates.extend(date.fromisoformat(r[c]) for c in cols if r[c])
    start, end = min(dates), max(dates)
    with (OUT / "date_dim.csv").open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["date", "year", "quarter", "month_number", "month_name", "year_month", "iso_week", "day", "day_of_week_number", "day_of_week_name"])
        current = start
        while current <= end:
            writer.writerow([current.isoformat(), current.year, f"Q{(current.month-1)//3+1}", current.month,
                             current.strftime("%B"), current.strftime("%Y-%m"), current.isocalendar().week,
                             current.day, current.isoweekday(), current.strftime("%A")])
            current += timedelta(days=1)
    manifest["date_dim"] = {"rows": (end-start).days+1, "start": str(start), "end": str(end),
                            "sha256": digest(OUT / "date_dim.csv"), "upstream": "DERIVED calendar from source and scenario dates"}
    assert manifest["daily_operations"]["rows"] == 76000
    assert manifest["demand_forecast_14d"]["rows"] == 1400
    assert manifest["local_skus"]["rows"] == 100
    assert manifest["locations"]["rows"] == 5
    assert manifest["suppliers"]["rows"] == 6
    assert manifest["purchase_orders"]["rows"] == manifest["receipts"]["rows"] == 5299
    sku = {r["local_sku_id"] for r in rows("local_skus")}
    suppliers = {r["supplier_id"] for r in rows("suppliers")}
    po = {r["po_id"] for r in rows("purchase_orders")}
    assert len(sku) == 100 and len(po) == 5299
    for name in ["daily_operations", "demand_forecast_14d", "replenishment_recommendations", "abc_inventory_classification", "supply_chain_priority_matrix", "forecast_holdout_predictions"]:
        assert all(r["local_sku_id"] in sku for r in rows(name)), name
    assert all(r["supplier_id"] in suppliers for r in rows("supplier_scorecard"))
    assert all(r["po_id"] in po for r in rows("receipts"))
    assert len({(r["date"], r["local_sku_id"]) for r in rows("daily_operations")}) == 76000
    assert len({(r["forecast_date"], r["local_sku_id"]) for r in rows("demand_forecast_14d")}) == 1400
    assert len({r["local_sku_id"] for r in rows("replenishment_recommendations")}) == 100
    assert len({r["local_sku_id"] for r in rows("abc_inventory_classification")}) == 100
    assert len({r["local_sku_id"] for r in rows("supply_chain_priority_matrix")}) == 100
    actual = sum(int(r["units_sold"]) for r in rows("daily_operations"))
    forecast = sum(float(r["predicted_units"]) for r in rows("demand_forecast_14d"))
    rec = list(rows("replenishment_recommendations"))
    abc = list(rows("abc_inventory_classification"))
    matrix = list(rows("supply_chain_priority_matrix"))
    scores = list(rows("supplier_scorecard"))
    anchors = {"historical_units": actual, "forecast_14d_units": round(forecast, 2),
               "latest_inventory": sum(int(r["current_inventory"]) for r in rec),
               "reorder_skus": sum(r["inventory_status"] == "REORDER REQUIRED" for r in rec),
               "recommended_units": sum(int(r["recommended_order_quantity"]) for r in rec),
               "abc": {x: sum(r["abc_class"] == x for r in abc) for x in "ABC"},
               "priority": {x: sum(r["management_priority"] == x for r in matrix) for x in ("CRITICAL", "HIGH", "MEDIUM")},
               "on_time_receipts": sum(int(r["on_time_receipts"]) for r in scores),
               "supplier_po_total": sum(int(r["purchase_orders"]) for r in scores)}
    assert anchors == {"historical_units": 6750876, "forecast_14d_units": 126137.36,
                       "latest_inventory": 29049, "reorder_skus": 97, "recommended_units": 180766,
                       "abc": {"A": 60, "B": 24, "C": 16},
                       "priority": {"CRITICAL": 23, "HIGH": 36, "MEDIUM": 41},
                       "on_time_receipts": 3316, "supplier_po_total": 5299}
    assert sum(int(r["purchase_orders"]) for r in scores) == len(po)
    assert all(0 <= float(r["on_time_pct"]) <= 100 and 0 <= float(r["receipt_fill_pct"]) <= 100 for r in scores)
    report = {"files": manifest, "anchors": anchors, "checks": "PASS: copied bytes, grain/keys, foreign references, counts, supplier percentages and totals"}
    (ROOT / "dashboard" / "phase9_validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"anchors": anchors, "date_range": [str(start), str(end)], "tables": {k:v["rows"] for k,v in manifest.items()}}, indent=2))


if __name__ == "__main__":
    run()
