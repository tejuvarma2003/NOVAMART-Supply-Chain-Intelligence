"""Run the approved Ridge artifact on its fixed 2024-01-30 origin, read-only."""
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from phase6_forecast import FEATURES, load_panel, make_rows

ROOT = Path(__file__).resolve().parents[1]


def main():
    artifact = joblib.load(ROOT / "models/selected_forecaster.joblib")
    assert artifact["name"] == "Ridge" and artifact["features"] == FEATURES
    source = load_panel()
    forward = make_rows(source, [pd.Timestamp(source.date.max())], future=True)
    prediction = np.maximum(0, artifact["model"].predict(forward[FEATURES]))
    approved = pd.read_csv(ROOT / "reports/demand_forecast_14d.csv")
    keys = forward[["forecast_date", "local_sku_id"]].copy()
    keys["forecast_date"] = keys["forecast_date"].dt.strftime("%Y-%m-%d")
    keys["predicted_units"] = prediction
    joined = approved.merge(keys, on=["forecast_date", "local_sku_id"],
                            validate="one_to_one", suffixes=("_approved", "_inference"))
    assert len(joined) == len(approved) == 1400
    assert np.allclose(joined.predicted_units_approved,
                       joined.predicted_units_inference, atol=5.1e-7, rtol=0)
    print(json.dumps({"status": "PASS", "model": artifact["name"],
                      "forecast_rows": len(joined),
                      "approved_rounded_total": round(float(approved.predicted_units.sum()), 2),
                      "saved_artifact_inference_total": round(float(prediction.sum()), 2),
                      "model_and_reports_modified": False}, indent=2))


if __name__ == "__main__":
    main()
