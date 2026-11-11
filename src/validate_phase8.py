"""Independent Phase 8 reconciliation, scoring direction, joins and repeatability."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1];R=ROOT/"reports";D=ROOT/"data/processed"
FILES=[R/x for x in ["abc_inventory_classification.csv","supplier_scorecard.csv","supply_chain_priority_matrix.csv","high_priority_supply_chain_actions.csv","phase8_summary.json"]]+sorted((ROOT/"images/abc_supplier").glob("*.png"))


def main():
    assert len(FILES)==11
    before={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in FILES}
    abc=pd.read_csv(R/"abc_inventory_classification.csv")
    score=pd.read_csv(R/"supplier_scorecard.csv")
    matrix=pd.read_csv(R/"supply_chain_priority_matrix.csv")
    source=pd.read_csv(D/"daily_operations.csv")
    phase7=pd.read_csv(R/"replenishment_recommendations.csv")
    sql=pd.read_csv(R/"supplier_performance.csv")
    mapping=pd.read_csv(D/"sku_supplier_map.csv")
    info=json.loads((R/"phase8_summary.json").read_text())
    assert len(abc)==abc.local_sku_id.nunique()==100
    assert abc.abc_class.isin(["A","B","C"]).all()
    assert abc.cumulative_value_pct.is_monotonic_increasing
    assert abs(abc.value_share_pct.sum()-100)<.001
    assert abs(abc.sales_value_proxy_2023.sum()-info["total_sales_value_proxy_2023"])<.001
    year=source[source.date.between("2023-01-01","2023-12-31")]
    assert len(year)==36500 and year.date.nunique()==365
    assert abs((year.units_sold*year.listed_price).sum()-abc.sales_value_proxy_2023.sum())<.001
    prior=abc.cumulative_value_pct-abc.value_share_pct
    expected=np.select([prior.lt(80),prior.lt(95)],["A","B"],default="C")
    assert np.array_equal(expected,abc.abc_class.to_numpy())
    assert len(score)==score.supplier_id.nunique()==6
    assert score.supplier_score_assumed_weights.between(0,100).all()
    assert score.supplier_score_alternative_weights.between(0,100).all()
    for field,up in [("on_time_pct",True),("receipt_fill_pct",True),("lead_sd_days",False),("avg_positive_delay_all_days",False)]:
        component={"on_time_pct":"on_time_score","receipt_fill_pct":"fill_score","lead_sd_days":"consistency_score","avg_positive_delay_all_days":"delay_score"}[field]
        ordered=score.sort_values(field)[component].to_numpy()
        assert (np.diff(ordered)>=-1e-7).all() if up else (np.diff(ordered)<=1e-7).all()
    recalc=.4*score.on_time_score+.3*score.fill_score+.2*score.consistency_score+.1*score.delay_score
    np.testing.assert_allclose(recalc,score.supplier_score_assumed_weights,atol=2e-6)
    for row in score.itertuples():
        ref=sql.set_index("supplier_id").loc[row.supplier_id]
        assert row.purchase_orders==ref.purchase_orders and row.ordered_units==ref.ordered_units and row.received_units==ref.received_units
        for a,b in [("on_time_pct","on_time_pct"),("late_pct","late_pct"),("receipt_fill_pct","receipt_fill_pct"),("lead_sd_days","actual_lead_sd_days"),("avg_positive_delay_all_days","avg_positive_delay_all_receipts_days"),("ordered_commitment","ordered_spend")]:
            assert abs(getattr(row,a)-ref[b])<.011,(row.supplier_id,a)
    assert len(matrix)==matrix.local_sku_id.nunique()==100
    assert len(matrix.merge(phase7[["local_sku_id","supplier_id"]],on=["local_sku_id","supplier_id"],validate="one_to_one"))==100
    assert len(matrix.merge(mapping[["local_sku_id","supplier_id"]],on=["local_sku_id","supplier_id"],validate="one_to_one"))==100
    needs=matrix.supplier_tier.eq("Needs Review");reorder=matrix.inventory_status.isin(["STOCKOUT","REORDER REQUIRED"])
    priority=np.select([matrix.abc_class.eq("A")&reorder&needs,
        (matrix.abc_class.eq("A")&reorder)|(matrix.abc_class.eq("B")&reorder&needs),
        reorder|(matrix.abc_class.eq("A")&matrix.inventory_status.ne("HEALTHY"))],
        ["CRITICAL","HIGH","MEDIUM"],default="ROUTINE")
    assert np.array_equal(priority,matrix.management_priority.to_numpy())
    assert hashlib.sha256((R/"replenishment_recommendations.csv").read_bytes()).hexdigest()==info["phase7_file_sha256"]
    subprocess.run([sys.executable,str(ROOT/"src/abc_supplier_analysis.py")],check=True,capture_output=True)
    assert before=={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in FILES}
    print(json.dumps({"result":"PASS","abc_skus":100,"suppliers":6,"combined_skus":100,
                      "abc_value_reconciliation":"PASS","sql_supplier_reconciliation":"PASS",
                      "score_directions_and_weights":"PASS","priority_and_join_checks":"PASS",
                      "reproducible_outputs":len(FILES)},indent=2))


if __name__=="__main__":main()
