"""Reconcile descriptive Python EDA to Phase 4 SQL and verify stable outputs."""
import hashlib
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
REP=ROOT/"reports"
IMG=ROOT/"images/eda"
EXPORTS=["sku_demand_profile.csv","inventory_eda_summary.csv","supplier_eda_summary.csv","phase5_metrics.json"]
CHARTS=sorted(IMG.glob("*.png"))


def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def validate():
    assert len(CHARTS)==9
    before={str(p.relative_to(ROOT)):digest(p) for p in [*(REP/x for x in EXPORTS),*CHARTS]}
    metrics=json.loads((REP/"phase5_metrics.json").read_text())
    profile=pd.read_csv(REP/"sku_demand_profile.csv")
    inv=pd.read_csv(REP/"inventory_eda_summary.csv")
    supplier=pd.read_csv(REP/"supplier_eda_summary.csv")
    sql_supplier=pd.read_csv(REP/"supplier_performance.csv")
    daily=pd.read_csv(ROOT/"data/processed/daily_operations.csv")
    assert len(daily)==76000 and daily.local_sku_id.nunique()==100
    assert (daily.date.min(),daily.date.max(),daily.date.nunique())==("2022-01-01","2024-01-30",760)
    assert profile.total_units.sum()==metrics["total_units_sold"]==6750876
    assert profile.zero_inventory_days.sum()==metrics["zero_inventory_days"]==406
    assert len(inv)==len(profile)==100 and inv.inventory_units.sum()==29049
    assert inv.coverage_days_proxy.lt(7).sum()==90
    assert metrics["simulated_po_count"]==supplier.purchase_orders.sum()==5299
    assert metrics["simulated_ontime_count"]==int(sql_supplier.on_time_receipts.sum())==3316
    assert metrics["simulated_late_count"]==int(sql_supplier.late_receipts.sum())==1983
    assert abs(supplier.ordered_commitment.sum()-sql_supplier.ordered_spend.sum())<.02
    for _,row in supplier.iterrows():
        ref=sql_supplier.set_index("supplier_id").loc[row.supplier_id]
        for a,b in [("on_time_pct","on_time_pct"),("late_pct","late_pct"),("mean_actual_lead_days","avg_actual_lead_days"),("lead_sd_days","actual_lead_sd_days"),("receipt_fill_pct","receipt_fill_pct")]:
            assert abs(row[a]-ref[b])<.011,(row.supplier_id,a)
    assert supplier.data_origin.eq("SIMULATED").all()
    assert daily.data_origin.eq("SOURCE_SYNTHETIC_PLUS_DERIVED").all()
    with sqlite3.connect(ROOT/"database/novamart_scm.db") as conn:
        assert conn.execute("SELECT SUM(units_sold),SUM(inventory_units=0) FROM daily_operations").fetchone()==(6750876,406)
    subprocess.run([sys.executable,str(ROOT/"src/phase5_eda.py")],check=True,capture_output=True)
    after={str(p.relative_to(ROOT)):digest(p) for p in [*(REP/x for x in EXPORTS),*CHARTS]}
    assert before==after,"EDA exports/charts changed after rerun"
    print(json.dumps({"result":"PASS","operational_rows":76000,"local_skus":100,"units_sold":6750876,"zero_inventory_days":406,"sql_supplier_reconciliation":"PASS","lineage":"PASS","reproducible_files":len(before)},indent=2))


if __name__=="__main__":validate()
