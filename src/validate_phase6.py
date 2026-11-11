"""Audit chronological separation, frozen-origin features, metrics, outputs, and rerun."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from phase6_forecast import load_panel, make_rows, VAL_ORIGINS, TEST_ORIGINS, metrics

ROOT=Path(__file__).resolve().parents[1];R=ROOT/"reports"
FILES=["forecast_model_comparison.csv","forecast_holdout_predictions.csv","forecast_error_by_sku.csv",
       "forecast_by_category.csv","forecast_by_location.csv","demand_forecast_14d.csv",
       "demand_forecast_14d_summary.csv","phase6_manifest.json"]


def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    manifest=json.loads((R/"phase6_manifest.json").read_text())
    comp=pd.read_csv(R/"forecast_model_comparison.csv")
    hold=pd.read_csv(R/"forecast_holdout_predictions.csv")
    forward=pd.read_csv(R/"demand_forecast_14d.csv")
    summary=pd.read_csv(R/"demand_forecast_14d_summary.csv")
    err=pd.read_csv(R/"forecast_error_by_sku.csv")
    assert manifest["train_target_max"]<manifest["validation_target_min"]
    assert manifest["validation_target_max"]<manifest["test_target_min"]
    assert len(hold)==14000 and len(err)==100 and err.oos_rows.eq(140).all()
    assert len(forward)==1400 and forward.local_sku_id.nunique()==100
    assert forward.groupby("local_sku_id").forecast_date.nunique().eq(14).all()
    assert forward.forecast_date.min()=="2024-01-31" and forward.forecast_date.max()=="2024-02-13"
    assert forward.predicted_units.ge(0).all() and np.isfinite(forward.predicted_units).all()
    assert len(summary)==100 and abs(summary.forecast_14d_units.sum()-forward.predicted_units.sum())<.001
    assert forward.data_origin.eq("MODEL_FORECAST_FROM_SOURCE_SYNTHETIC").all()
    for split,g in hold.groupby("split"):
        assert (g.forecast_date>g.origin_date).all()
        for _,row in comp[comp.split.eq(split)].iterrows():
            calc=metrics(g.actual,g[row.model])
            for key in ["MAE","RMSE","WAPE_pct"]:assert abs(calc[key]-row[key])<.000002,(split,row.model,key)
    assert np.isfinite(hold[["naive_last","mean_7","mean_28"]].to_numpy()).all()
    # Rebuild features at one origin, then perturb only later actual sales. All
    # features and direct 14-day forecasts' inputs must remain unchanged.
    panel=load_panel();origin=pd.Timestamp("2023-11-11")
    base=make_rows(panel,[origin]);altered=panel.copy()
    altered.loc[altered.date.gt(origin),"units_sold"]+=10000
    changed=make_rows(altered,[origin])
    feature_cols=["last_sales","lag_7","lag_14","lag_28","mean_7","mean_14","mean_28","std_7","std_28","target_dow","target_month","target_weekend"]
    assert base[feature_cols].equals(changed[feature_cols])
    assert len(base)==1400 and base.horizon_day.between(1,14).all()
    # Concrete hand-calculation verifies shifted rolling and lag semantics.
    sku=panel.local_sku_id.min();history=panel[(panel.local_sku_id.eq(sku)) & (panel.date.le(origin))].sort_values("date").units_sold
    row=base[base.local_sku_id.eq(sku)].iloc[0]
    assert row.last_sales==history.iloc[-1] and row.lag_7==history.iloc[-7]
    assert row.lag_28==history.iloc[-28] and abs(row.mean_28-history.iloc[-28:].mean())<1e-12
    files=[*(R/name for name in FILES),*sorted((ROOT/"images/forecasting").glob("*.png"))]
    assert len(files)==13
    before={str(x.relative_to(ROOT)):digest(x) for x in files}
    subprocess.run([sys.executable,str(ROOT/"src/phase6_forecast.py")],check=True,capture_output=True)
    after={str(x.relative_to(ROOT)):digest(x) for x in files}
    assert before==after,"Forecast reports or charts changed on rerun"
    print(json.dumps({"result":"PASS","chrono_split":"PASS","future_target_perturbation":"PASS",
                      "baseline_and_model_metrics":"PASS","forward_sku_days":len(forward),
                      "oos_error_skus":len(err),"reproducible_outputs":len(files)},indent=2))


if __name__=="__main__":main()
