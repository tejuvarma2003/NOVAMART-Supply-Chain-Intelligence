"""Read-only project smoke test and approved KPI reconciliation."""
import json
import sqlite3
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from phase6_forecast import FEATURES, load_panel, make_rows

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"


def main():
    with sqlite3.connect(ROOT / "database/novamart_scm.db") as db:
        db.execute("PRAGMA foreign_keys=ON")
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert not db.execute("PRAGMA foreign_key_check").fetchall()
        sales = db.execute("SELECT SUM(units_sold) FROM daily_operations").fetchone()[0]
        npo = db.execute("SELECT COUNT(*) FROM purchase_orders").fetchone()[0]
        on_time = db.execute("""SELECT SUM(r.actual_delivery_date <= p.expected_delivery_date)
                                FROM receipts r JOIN purchase_orders p USING(po_id)""").fetchone()[0]
    forward = pd.read_csv(REPORTS / "demand_forecast_14d.csv")
    inv = pd.read_csv(REPORTS / "replenishment_recommendations.csv")
    abc = pd.read_csv(REPORTS / "abc_inventory_classification.csv")
    priority = pd.read_csv(REPORTS / "supply_chain_priority_matrix.csv")
    comparison = pd.read_csv(REPORTS / "forecast_model_comparison.csv")
    selected = comparison[(comparison.split == "test") & (comparison.model == "Ridge")].iloc[0]
    package = joblib.load(ROOT / "models/selected_forecaster.joblib")
    assert package["name"] == "Ridge" and package["features"] == FEATURES
    # Inference on one frozen-origin feature row verifies model deserialization
    # without fitting or modifying the approved artifact.
    panel = load_panel()
    features = make_rows(panel, [pd.Timestamp(panel.date.max())], future=True)
    prediction = package["model"].predict(features[FEATURES].iloc[:1])
    assert prediction.shape == (1,) and np.isfinite(prediction).all()
    assert len(forward) == 1400 and forward.local_sku_id.nunique() == 100
    assert (forward.forecast_date.min(), forward.forecast_date.max()) == ("2024-01-31", "2024-02-13")
    result = {
        "historical_units_sold": int(sales),
        "forecast_14d_units": round(float(forward.predicted_units.sum()), 2),
        "latest_inventory_units": int(inv.current_inventory.sum()),
        "reorder_cases": int(inv.inventory_status.eq("REORDER REQUIRED").sum()),
        "recommended_order_units": int(inv.recommended_order_quantity.sum()),
        "abc_counts": {key: int(abc.abc_class.eq(key).sum()) for key in "ABC"},
        "priority_counts": {key: int(priority.management_priority.eq(key).sum()) for key in ("CRITICAL", "HIGH", "MEDIUM")},
        "simulated_ontime_pct": round(on_time / npo * 100, 2),
        "ridge_test_wape_pct": round(float(selected.WAPE_pct), 2),
        "model_load_and_inference": "PASS",
    }
    expected = {
        "historical_units_sold": 6750876, "forecast_14d_units": 126137.36,
        "latest_inventory_units": 29049, "reorder_cases": 97,
        "recommended_order_units": 180766,
        "abc_counts": {"A": 60, "B": 24, "C": 16},
        "priority_counts": {"CRITICAL": 23, "HIGH": 36, "MEDIUM": 41},
        "simulated_ontime_pct": 62.58, "ridge_test_wape_pct": 37.34,
        "model_load_and_inference": "PASS",
    }
    assert result == expected, (result, expected)
    print(json.dumps({"result": "PASS", **result}, indent=2))


if __name__ == "__main__":
    main()
