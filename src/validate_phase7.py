"""Independent Phase 7 formula, join, lineage and deterministic-output checks."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1];R=ROOT/"reports";D=ROOT/"data/processed"
FILES=[R/x for x in ["replenishment_recommendations.csv","inventory_exceptions.csv","eoq_sensitivity.csv","phase7_kpi_summary.json"]]+sorted((ROOT/"images/inventory").glob("*.png"))


def main():
    assert len(FILES)==10
    hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in FILES}
    out=pd.read_csv(R/"replenishment_recommendations.csv")
    f=pd.read_csv(R/"demand_forecast_14d_summary.csv")
    err=pd.read_csv(R/"forecast_error_by_sku.csv")
    source=pd.read_csv(D/"daily_operations.csv")
    mapping=pd.read_csv(D/"sku_supplier_map.csv")
    info=json.loads((R/"phase7_kpi_summary.json").read_text())
    assert len(out)==100 and out.local_sku_id.nunique()==100
    assert len(out.merge(f,on=["local_sku_id","location_id"],validate="one_to_one"))==100
    assert len(out.merge(err[["local_sku_id"]],on="local_sku_id",validate="one_to_one"))==100
    assert len(out.merge(mapping[["local_sku_id","supplier_id"]],on=["local_sku_id","supplier_id"],validate="one_to_one"))==100
    assert out.supplier_id.notna().all() and out.expected_lead_time_days.gt(0).all()
    assert out[["safety_stock","reorder_point","eoq_reference"]].ge(0).all().all() and out.eoq_reference.gt(0).all()
    assert out.recommended_order_quantity.ge(0).all() and (out.recommended_order_quantity%1==0).all()
    assert out.snapshot_date.eq(source.date.max()).all()
    latest=source[source.date.eq(source.date.max())].set_index("local_sku_id")
    assert all(int(row.current_inventory)==int(latest.loc[row.local_sku_id,"inventory_units"]) for row in out.itertuples())
    assert hashlib.sha256((D/"daily_operations.csv").read_bytes()).hexdigest()==info["source_inventory_sha256"]
    # Recalculate all continuous quantities before final rounding.
    np.testing.assert_allclose(out.forecast_14d_units/14,out.avg_forecast_daily_units,atol=1e-6)
    np.testing.assert_allclose(out.avg_forecast_daily_units*out.expected_lead_time_days,out.lead_time_demand,atol=1e-5)
    np.testing.assert_allclose(1.645*out.forecast_error_std*np.sqrt(out.expected_lead_time_days),out.safety_stock,atol=1e-5)
    np.testing.assert_allclose(out.lead_time_demand+out.safety_stock,out.reorder_point,atol=2e-6)
    np.testing.assert_allclose(out.avg_forecast_daily_units*(out.expected_lead_time_days+14)+out.safety_stock,out.target_stock,atol=2e-5)
    np.testing.assert_allclose(np.sqrt(2*out.annual_demand_proxy*75/(out.procurement_unit_cost*.20)),out.eoq_reference,atol=2e-5)
    status=np.select([out.current_inventory.le(0),out.current_inventory.le(out.reorder_point),
                      out.current_inventory.gt(2*out.target_stock),out.current_inventory.lt(out.target_stock)],
                     ["STOCKOUT","REORDER REQUIRED","EXCESS INVENTORY","LOW STOCK / AT RISK"],default="HEALTHY")
    assert (out.inventory_status==status).all()
    expected=np.where(np.isin(status,["STOCKOUT","REORDER REQUIRED"]),np.ceil(np.maximum(0,out.target_stock-out.current_inventory)),0).astype(int)
    assert np.array_equal(out.recommended_order_quantity.to_numpy(),expected)
    priorities=np.select([status=="STOCKOUT",status=="REORDER REQUIRED",np.isin(status,["LOW STOCK / AT RISK","EXCESS INVENTORY"])],["CRITICAL","HIGH","MEDIUM"],default="NO ACTION")
    assert (out.recommendation_priority==priorities).all()
    assert int(out.recommended_order_quantity.sum())==info["recommended_units"]
    assert out.inventory_origin.eq("SOURCE_SYNTHETIC_SNAPSHOT").all()
    assert out.demand_origin.eq("MODEL_FORECAST_FROM_SOURCE_SYNTHETIC").all()
    assert out.supplier_cost_origin.eq("SIMULATED").all()
    for sku in ["S001_P0001","S001_P0003","S001_P0010"]:
        r=out.set_index("local_sku_id").loc[sku]
        print(f"{sku}: forecast14={r.forecast_14d_units:.2f}, daily={r.avg_forecast_daily_units:.2f}, lead={r.expected_lead_time_days}, lead_demand={r.lead_time_demand:.2f}, error_sd={r.forecast_error_std:.2f}, safety={r.safety_stock:.2f}, ROP={r.reorder_point:.2f}, stock={r.current_inventory}, EOQ={r.eoq_reference:.2f}, order={r.recommended_order_quantity}, action={r.inventory_status}")
    subprocess.run([sys.executable,str(ROOT/"src/inventory_optimization.py")],check=True,capture_output=True)
    assert hashes=={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in FILES}
    print(json.dumps({"result":"PASS","local_skus":100,"supplier_and_forecast_joins":"PASS","formula_and_priority_checks":"PASS","unchanged_source":"PASS","reproducible_outputs":len(FILES)},indent=2))


if __name__=="__main__":main()
