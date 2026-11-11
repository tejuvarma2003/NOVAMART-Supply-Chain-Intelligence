"""Integrity and reproducibility checks for the Phase 3 CSV foundation."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "data/processed"


def validate():
    names = ["locations", "local_skus", "daily_operations", "suppliers", "sku_supplier_map", "purchase_orders", "receipts"]
    t = {name:pd.read_csv(P/f"{name}.csv") for name in names}
    l,s,d,v,m,po,r = (t[n] for n in names)
    for table,keys in [(l,["location_id"]),(s,["local_sku_id"]),(d,["date","local_sku_id"]),(v,["supplier_id"]),(m,["local_sku_id","supplier_id"]),(po,["po_id"]),(r,["receipt_id"]),(r,["po_id"])]:
        assert not table.duplicated(keys).any(), keys
    for frame,field,parent in [(s,"location_id",l.location_id),(d,"location_id",l.location_id),
                               (d,"local_sku_id",s.local_sku_id),(m,"local_sku_id",s.local_sku_id),
                               (m,"supplier_id",v.supplier_id),(po,"supplier_id",v.supplier_id),
                               (po,"local_sku_id",s.local_sku_id),(po,"location_id",l.location_id),
                               (r,"po_id",po.po_id)]:
        assert frame[field].notna().all() and frame[field].isin(parent).all(), field
    assert s.groupby("local_sku_id")["location_id"].nunique().eq(1).all()
    assert s.groupby("local_sku_id")["category"].nunique().eq(1).all()
    assert (s.local_sku_id == s.location_id + "_" + s.original_product_id).all()
    assert len(l)==5 and len(s)==100 and len(d)==76000
    assert d.groupby("local_sku_id").date.nunique().eq(760).all()
    assert not d.isna().any().any()
    assert d.date.min()=="2022-01-01" and d.date.max()=="2024-01-30"
    assert d.sort_values(["date","location_id","local_sku_id"]).index.equals(d.index)
    assert m.groupby("local_sku_id").primary_supplier_flag.sum().eq(1).all()
    assert s.local_sku_id.isin(m.local_sku_id).all()
    assert (po.ordered_quantity > 0).all() and (po.procurement_unit_cost > 0).all()
    assert (r.received_quantity >= 0).all()
    assert (pd.to_datetime(po.expected_delivery_date)>=pd.to_datetime(po.order_date)).all()
    joined = r.merge(po[["po_id","order_date","expected_delivery_date","ordered_quantity"]],on="po_id",validate="one_to_one")
    assert (pd.to_datetime(joined.actual_delivery_date)>=pd.to_datetime(joined.order_date)).all()
    assert (joined.received_quantity<=joined.ordered_quantity).all()
    assert po.merge(s[["local_sku_id","location_id"]],on="local_sku_id",suffixes=("","_sku")).eval("location_id == location_id_sku").all()
    assert po.merge(m[["local_sku_id","supplier_id"]],on=["local_sku_id","supplier_id"],validate="many_to_one").shape[0]==len(po)
    assert set(v.data_origin)=={"SIMULATED"} and set(po.data_origin)=={"SIMULATED"} and set(r.data_origin)=={"SIMULATED"}
    assert set(d.data_origin)=={"SOURCE_SYNTHETIC_PLUS_DERIVED"}
    for col in ["inventory_units","units_sold","units_ordered_source","estimated_demand_source"]:
        assert d[col].ge(0).all()
    manifest=json.loads((P/"phase3_manifest.json").read_text())
    before={n:hashlib.sha256((P/f"{n}.csv").read_bytes()).hexdigest() for n in names}
    assert all(manifest["tables"][n]["sha256"]==before[n] and manifest["tables"][n]["rows"]==len(t[n]) for n in names)
    subprocess.run([sys.executable,str(ROOT/"src/build_phase3.py")],check=True,capture_output=True)
    after={n:hashlib.sha256((P/f"{n}.csv").read_bytes()).hexdigest() for n in names}
    assert before==after, "Seeded generation changed outputs"
    print(json.dumps({"result":"PASS","table_rows":{n:len(t[n]) for n in names},"duplicate_and_foreign_keys":"PASS","daily_coverage":"PASS","date_quantity_cost_checks":"PASS","lineage":"PASS","reproducible_sha256":"PASS"},indent=2))


if __name__=="__main__":
    validate()
