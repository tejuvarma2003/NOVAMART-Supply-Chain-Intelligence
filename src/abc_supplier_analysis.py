"""Phase 8 ABC value prioritization and simulated supplier scenario scoring."""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1];D=ROOT/"data/processed";R=ROOT/"reports";IMG=ROOT/"images/abc_supplier"
BASE={"on_time_score":.40,"fill_score":.30,"consistency_score":.20,"delay_score":.10}
ALT={"on_time_score":.25,"fill_score":.35,"consistency_score":.25,"delay_score":.15}


def scale(s, higher=True):
    low,high=s.min(),s.max()
    if high==low:return pd.Series(100.,index=s.index)
    return 100*(s-low)/(high-low) if higher else 100*(high-s)/(high-low)


def weighted(df,weights):return sum(df[key]*weight for key,weight in weights.items())


def build():
    IMG.mkdir(parents=True,exist_ok=True)
    assert abs(sum(BASE.values())-1)<1e-12 and abs(sum(ALT.values())-1)<1e-12
    d=pd.read_csv(D/"daily_operations.csv")
    skus=pd.read_csv(D/"local_skus.csv")
    recommend=pd.read_csv(R/"replenishment_recommendations.csv")
    po=pd.read_csv(D/"purchase_orders.csv",parse_dates=["order_date","expected_delivery_date"])
    receipt=pd.read_csv(D/"receipts.csv",parse_dates=["actual_delivery_date"])
    suppliers=pd.read_csv(D/"suppliers.csv")
    assert len(d)==76000 and len(recommend)==100
    year=d[d.date.between("2023-01-01","2023-12-31")].copy()
    assert len(year)==36500 and year.date.nunique()==365
    year["sales_value_proxy"]=year.units_sold*year.listed_price
    abc=year.groupby("local_sku_id",as_index=False).agg(units_2023=("units_sold","sum"),sales_value_proxy_2023=("sales_value_proxy","sum"))
    abc=abc.merge(skus[["local_sku_id","location_id","category"]],on="local_sku_id",validate="one_to_one")
    abc=abc.sort_values(["sales_value_proxy_2023","local_sku_id"],ascending=[False,True]).reset_index(drop=True)
    total=abc.sales_value_proxy_2023.sum()
    abc["value_share_pct"]=100*abc.sales_value_proxy_2023/total
    abc["cumulative_value_pct"]=abc.value_share_pct.cumsum()
    prior=abc.cumulative_value_pct-abc.value_share_pct
    abc["abc_class"]=np.select([prior.lt(80),prior.lt(95)],["A","B"],default="C")
    abc["value_origin"]="SOURCE_SYNTHETIC_DERIVED_SALES_VALUE_PROXY"
    abc.to_csv(R/"abc_inventory_classification.csv",index=False,float_format="%.6f")

    events=po.merge(receipt,on="po_id",validate="one_to_one")
    assert len(events)==5299 and events.data_origin_x.eq("SIMULATED").all() and events.data_origin_y.eq("SIMULATED").all()
    events["actual_lead_days"]=(events.actual_delivery_date-events.order_date).dt.days
    events["delay_days"]=(events.actual_delivery_date-events.expected_delivery_date).dt.days
    events["late"]=events.delay_days.gt(0)
    events["ordered_commitment"]=events.ordered_quantity*events.procurement_unit_cost
    score=events.groupby("supplier_id",as_index=False).agg(purchase_orders=("po_id","size"),ordered_units=("ordered_quantity","sum"),
        received_units=("received_quantity","sum"),ordered_commitment=("ordered_commitment","sum"),
        on_time_receipts=("late",lambda x:int((~x).sum())),late_receipts=("late","sum"),
        avg_actual_lead_days=("actual_lead_days","mean"),lead_sd_days=("actual_lead_days",lambda x:x.std(ddof=0)),
        avg_positive_delay_all_days=("delay_days",lambda x:x.clip(lower=0).mean()))
    score=score.merge(suppliers[["supplier_id","supplier_name"]],on="supplier_id",validate="one_to_one")
    score["on_time_pct"]=100*score.on_time_receipts/score.purchase_orders
    score["late_pct"]=100*score.late_receipts/score.purchase_orders
    score["receipt_fill_pct"]=100*score.received_units/score.ordered_units
    score["on_time_score"]=scale(score.on_time_pct,True)
    score["fill_score"]=scale(score.receipt_fill_pct,True)
    score["consistency_score"]=scale(score.lead_sd_days,False)
    score["delay_score"]=scale(score.avg_positive_delay_all_days,False)
    score["supplier_score_assumed_weights"]=weighted(score,BASE)
    score["supplier_score_alternative_weights"]=weighted(score,ALT)
    score["base_rank"]=score.supplier_score_assumed_weights.rank(ascending=False,method="min").astype(int)
    score["alternative_rank"]=score.supplier_score_alternative_weights.rank(ascending=False,method="min").astype(int)
    score["supplier_tier"]=np.select([score.supplier_score_assumed_weights.ge(70),score.supplier_score_assumed_weights.ge(40)],
                                      ["Strong","Moderate"],default="Needs Review")
    score["data_origin"]="SIMULATED_OUTCOMES_DERIVED_SCORE_ASSUMED_WEIGHTS"
    score=score.sort_values("supplier_id").reset_index(drop=True)
    score.to_csv(R/"supplier_scorecard.csv",index=False,float_format="%.6f")

    combined=recommend.merge(abc[["local_sku_id","abc_class","units_2023","sales_value_proxy_2023","value_share_pct"]],on="local_sku_id",validate="one_to_one")
    combined=combined.merge(score[["supplier_id","supplier_name","on_time_pct","late_pct","receipt_fill_pct","lead_sd_days","supplier_score_assumed_weights","supplier_tier"]],on="supplier_id",validate="many_to_one")
    assert len(combined)==100
    reorder=combined.inventory_status.isin(["STOCKOUT","REORDER REQUIRED"])
    concerns=combined.supplier_tier.eq("Needs Review")
    combined["management_priority"]=np.select([
        combined.abc_class.eq("A") & reorder & concerns,
        (combined.abc_class.eq("A") & reorder) | (combined.abc_class.eq("B") & reorder & concerns),
        reorder | (combined.abc_class.eq("A") & combined.inventory_status.ne("HEALTHY"))],
        ["CRITICAL","HIGH","MEDIUM"],default="ROUTINE")
    combined["management_reason"]=np.select([
        combined.management_priority.eq("CRITICAL"),combined.management_priority.eq("HIGH"),combined.management_priority.eq("MEDIUM")],
        ["A value + reorder + supplier review","A reorder or B reorder + supplier review","Reorder or A inventory exception"],default="Routine monitoring")
    cols=["local_sku_id","location_id","category","abc_class","sales_value_proxy_2023","current_inventory","reorder_point","inventory_status",
          "forecast_14d_units","forecast_error_std","recommended_order_quantity","recommendation_priority","supplier_id","supplier_name",
          "on_time_pct","receipt_fill_pct","lead_sd_days","supplier_score_assumed_weights","supplier_tier","management_priority","management_reason",
          "inventory_origin","demand_origin","supplier_cost_origin","policy_origin"]
    combined=combined[cols].sort_values("local_sku_id")
    combined.to_csv(R/"supply_chain_priority_matrix.csv",index=False,float_format="%.6f")
    combined[combined.management_priority.isin(["CRITICAL","HIGH"])].sort_values(["management_priority","sales_value_proxy_2023"],ascending=[True,False]).to_csv(
        R/"high_priority_supply_chain_actions.csv",index=False,float_format="%.6f")

    metrics={"abc_counts":abc.abc_class.value_counts().to_dict(),
             "abc_value_share_pct":{k:round(float(v),3) for k,v in abc.groupby("abc_class").sales_value_proxy_2023.sum().div(total).mul(100).items()},
             "abc_units_share_pct":{k:round(float(v),3) for k,v in abc.groupby("abc_class").units_2023.sum().div(abc.units_2023.sum()).mul(100).items()},
             "total_sales_value_proxy_2023":round(float(total),2),
             "reorder_by_abc":combined[reorder].abc_class.value_counts().to_dict(),
             "management_priority_counts":combined.management_priority.value_counts().to_dict(),
             "tier_counts":score.supplier_tier.value_counts().to_dict(),
             "supplier_rank_changed":int(score.base_rank.ne(score.alternative_rank).sum()),
             "phase7_file_sha256":hashlib.sha256((R/"replenishment_recommendations.csv").read_bytes()).hexdigest()}
    (R/"phase8_summary.json").write_text(json.dumps(metrics,indent=2)+"\n")

    plt.rcParams.update({"font.size":10,"axes.spines.top":False,"axes.spines.right":False})
    def save(fig,name):fig.tight_layout();fig.savefig(IMG/name,dpi=160,facecolor="white");plt.close(fig)
    fig,ax=plt.subplots(figsize=(9,4));ax.plot(np.arange(1,101),abc.cumulative_value_pct,color="#168f8b");ax.axhline(80,ls="--",color="#e77e65");ax.axhline(95,ls="--",color="#e77e65");ax.set(xlabel="Local SKUs sorted by 2023 sales-value proxy",ylabel="Cumulative value (%)",title="ABC cumulative value (source synthetic price proxy)");save(fig,"01_abc_cumulative.png")
    classes=["A","B","C"];fig,axes=plt.subplots(1,2,figsize=(10,4));axes[0].bar(classes,[metrics["abc_counts"].get(c,0) for c in classes],color="#168f8b");axes[0].set(title="Local SKU count",ylabel="SKUs");axes[1].bar(classes,[metrics["abc_value_share_pct"].get(c,0) for c in classes],color="#e77e65");axes[1].set(title="2023 sales-value proxy share",ylabel="Percent");save(fig,"02_abc_count_value.png")
    fig,ax=plt.subplots(figsize=(7,4));ax.bar(classes,[metrics["reorder_by_abc"].get(c,0) for c in classes],color="#168f8b");ax.set(title="Reorder-required local SKUs by ABC class",xlabel="ABC class",ylabel="Local SKUs");save(fig,"03_reorder_by_abc.png")
    fig,ax=plt.subplots(figsize=(7,5));ax.scatter(score.on_time_pct,score.receipt_fill_pct,s=90,color="#168f8b");
    for row in score.itertuples():ax.annotate(row.supplier_id,(row.on_time_pct,row.receipt_fill_pct),xytext=(4,4),textcoords="offset points")
    ax.set(title="SIMULATED supplier delivery and fill",xlabel="On-time receipts (%)",ylabel="Receipt fill (%)");save(fig,"04_supplier_on_time_fill.png")
    fig,ax=plt.subplots(figsize=(8,4));ax.barh(score.supplier_id,score.supplier_score_assumed_weights,color="#168f8b");ax.set(xlim=(0,100),title="SIMULATED supplier score (assumed weights)",xlabel="Composite score / 100");save(fig,"05_supplier_scores.png")
    matrix=pd.crosstab(combined.abc_class,combined.management_priority).reindex(index=classes,columns=["CRITICAL","HIGH","MEDIUM","ROUTINE"],fill_value=0)
    fig,ax=plt.subplots(figsize=(8,4));im=ax.imshow(matrix,cmap="YlOrRd");ax.set_xticks(range(4),matrix.columns);ax.set_yticks(range(3),classes);ax.set(title="ABC class × management priority (scenario SKU count)",xlabel="Management priority",ylabel="ABC class")
    for i in range(3):
        for j in range(4):ax.text(j,i,str(matrix.iloc[i,j]),ha="center",va="center")
    fig.colorbar(im,ax=ax,label="Local SKUs");save(fig,"06_priority_matrix.png")
    return metrics


if __name__=="__main__":print(json.dumps(build(),indent=2))
