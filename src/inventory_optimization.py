"""Phase 7 scenario inventory policy; no source data is modified."""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data/processed"; REP=ROOT/"reports"; IMG=ROOT/"images/inventory"
Z=1.645; SERVICE=.95; ORDER_COST=75.; HOLD_RATE=.20; REVIEW_DAYS=14


def build():
    IMG.mkdir(parents=True,exist_ok=True)
    d=pd.read_csv(DATA/"daily_operations.csv",parse_dates=["date"])
    sku=pd.read_csv(DATA/"local_skus.csv")
    sourcing=pd.read_csv(DATA/"sku_supplier_map.csv")
    forecasts=pd.read_csv(REP/"demand_forecast_14d_summary.csv")
    daily_forecast=pd.read_csv(REP/"demand_forecast_14d.csv")
    errors=pd.read_csv(REP/"forecast_error_by_sku.csv")
    latest_date=d.date.max()
    latest=d[d.date.eq(latest_date)][["local_sku_id","location_id","inventory_units"]].copy()
    assert len(latest)==100 and daily_forecast.forecast_date.min()>str(latest_date.date())
    assert sourcing.primary_supplier_flag.eq(1).all()
    out=sku.merge(latest,on=["local_sku_id","location_id"],validate="one_to_one")
    out=out.merge(sourcing[["local_sku_id","supplier_id","expected_lead_time_days","procurement_unit_cost"]],on="local_sku_id",validate="one_to_one")
    out=out.merge(forecasts,on=["local_sku_id","location_id"],validate="one_to_one")
    out=out.merge(errors[["local_sku_id","forecast_error_std","forecast_mae","WAPE_pct"]],on="local_sku_id",validate="one_to_one")
    assert len(out)==100 and not out.isna().any().any()
    out=out.rename(columns={"inventory_units":"current_inventory","forecast_14d_units":"forecast_14d_units",
                            "average_forecast_daily_units":"avg_forecast_daily_units"})
    out["snapshot_date"]=str(latest_date.date())
    out["service_level_assumed"]=SERVICE
    out["z_value_assumed"]=Z
    out["ordering_cost_assumed"]=ORDER_COST
    out["holding_rate_assumed"]=HOLD_RATE
    out["lead_time_demand"]=out.avg_forecast_daily_units*out.expected_lead_time_days
    out["safety_stock"]=Z*out.forecast_error_std*np.sqrt(out.expected_lead_time_days)
    out["reorder_point"]=out.lead_time_demand+out.safety_stock
    out["target_stock"]=out.avg_forecast_daily_units*(out.expected_lead_time_days+REVIEW_DAYS)+out.safety_stock
    out["annual_demand_proxy"]=out.avg_forecast_daily_units*365
    out["annual_holding_cost_per_unit_assumed"]=out.procurement_unit_cost*HOLD_RATE
    out["eoq_reference"]=np.sqrt(2*out.annual_demand_proxy*ORDER_COST/out.annual_holding_cost_per_unit_assumed)
    out["coverage_days_proxy"]=np.where(out.avg_forecast_daily_units>0,out.current_inventory/out.avg_forecast_daily_units,np.nan)
    conditions=[out.current_inventory.le(0),out.current_inventory.le(out.reorder_point),
                out.current_inventory.gt(2*out.target_stock),out.current_inventory.lt(out.target_stock)]
    labels=["STOCKOUT","REORDER REQUIRED","EXCESS INVENTORY","LOW STOCK / AT RISK"]
    out["inventory_status"]=np.select(conditions,labels,default="HEALTHY")
    reorder=out.inventory_status.isin(["STOCKOUT","REORDER REQUIRED"])
    out["recommended_order_quantity"]=np.where(reorder,np.ceil(np.maximum(0,out.target_stock-out.current_inventory)),0).astype(int)
    out["recommendation_priority"]=np.select([out.inventory_status.eq("STOCKOUT"),out.inventory_status.eq("REORDER REQUIRED"),
                                                 out.inventory_status.isin(["LOW STOCK / AT RISK","EXCESS INVENTORY"])],
                                                ["CRITICAL","HIGH","MEDIUM"],default="NO ACTION")
    cutoff=out.avg_forecast_daily_units.quantile(.25)
    out["potential_slow_moving"]=out.avg_forecast_daily_units.le(cutoff) & out.coverage_days_proxy.gt(2*(out.expected_lead_time_days+REVIEW_DAYS))
    out["inventory_origin"]="SOURCE_SYNTHETIC_SNAPSHOT"
    out["demand_origin"]="MODEL_FORECAST_FROM_SOURCE_SYNTHETIC"
    out["supplier_cost_origin"]="SIMULATED"
    out["policy_origin"]="DERIVED_WITH_ASSUMPTIONS"
    ordered=["snapshot_date","local_sku_id","location_id","category","supplier_id","current_inventory",
             "forecast_14d_units","avg_forecast_daily_units","expected_lead_time_days","lead_time_demand",
             "forecast_error_std","service_level_assumed","z_value_assumed","safety_stock","reorder_point",
             "target_stock","annual_demand_proxy","procurement_unit_cost","ordering_cost_assumed",
             "holding_rate_assumed","annual_holding_cost_per_unit_assumed","eoq_reference","coverage_days_proxy",
             "inventory_status","potential_slow_moving","recommended_order_quantity","recommendation_priority",
             "inventory_origin","demand_origin","supplier_cost_origin","policy_origin"]
    out=out[ordered].sort_values("local_sku_id").reset_index(drop=True)
    out.to_csv(REP/"replenishment_recommendations.csv",index=False,float_format="%.6f")
    attention=out[(out.recommendation_priority.ne("NO ACTION")) | out.potential_slow_moving].copy()
    attention.to_csv(REP/"inventory_exceptions.csv",index=False,float_format="%.6f")
    sensitivity=[]
    for cost in [40.,75.,120.]:
        for rate in [.15,.20,.30]:
            values=np.sqrt(2*out.annual_demand_proxy*cost/(out.procurement_unit_cost*rate))
            sensitivity.append({"ordering_cost_assumed":cost,"holding_rate_assumed":rate,"mean_eoq_units":values.mean(),"median_eoq_units":values.median(),"min_eoq_units":values.min(),"max_eoq_units":values.max()})
    sens=pd.DataFrame(sensitivity)
    sens.to_csv(REP/"eoq_sensitivity.csv",index=False,float_format="%.6f")
    status=out.inventory_status.value_counts().to_dict();priority=out.recommendation_priority.value_counts().to_dict()
    summary={"snapshot_date":str(latest_date.date()),"local_skus":len(out),"status_counts":status,"priority_counts":priority,
             "recommended_units":int(out.recommended_order_quantity.sum()),"average_safety_stock":round(float(out.safety_stock.mean()),3),
             "mean_eoq_reference":round(float(out.eoq_reference.mean()),3),
             "mean_coverage_days":round(float(out.coverage_days_proxy.mean()),3),
             "potential_slow_moving":int(out.potential_slow_moving.sum()),"attention_rows":len(attention),
             "source_inventory_sha256":hashlib.sha256((DATA/"daily_operations.csv").read_bytes()).hexdigest()}
    (REP/"phase7_kpi_summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    plt.rcParams.update({"font.size":10,"axes.spines.top":False,"axes.spines.right":False})
    def save(fig,name):fig.tight_layout();fig.savefig(IMG/name,dpi=160,facecolor="white");plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,4));ax.barh(list(status),list(status.values()),color="#168f8b");ax.set(title="Inventory status at 2024-01-30 (scenario policy)",xlabel="Local SKUs");save(fig,"01_inventory_status.png")
    fig,ax=plt.subplots(figsize=(7,5));ax.scatter(out.reorder_point,out.current_inventory,c=out.recommended_order_quantity,cmap="viridis",s=30);lims=[0,max(out.reorder_point.max(),out.current_inventory.max())*1.05];ax.plot(lims,lims,"--",color="#e77e65",label="Inventory = reorder point");ax.set(xlabel="Reorder point (units)",ylabel="Latest inventory (units)",title="Snapshot inventory versus scenario reorder point");ax.legend();save(fig,"02_inventory_vs_reorder.png")
    fig,ax=plt.subplots(figsize=(8,4));out.groupby("category").safety_stock.mean().sort_values().plot.barh(ax=ax,color="#168f8b");ax.set(title="Average scenario safety stock by category",xlabel="Units per local SKU",ylabel="Category");save(fig,"03_safety_stock_category.png")
    fig,ax=plt.subplots(figsize=(8,4));ax.hist(out.coverage_days_proxy.dropna(),bins=20,color="#168f8b",edgecolor="white");ax.set(title="Latest inventory / forecast daily demand",xlabel="Coverage days proxy",ylabel="Local SKUs");save(fig,"04_coverage_distribution.png")
    top=out.nlargest(12,"recommended_order_quantity").sort_values("recommended_order_quantity")
    fig,ax=plt.subplots(figsize=(9,5));ax.barh(top.local_sku_id,top.recommended_order_quantity,color="#e77e65");ax.set(title="Top 12 proposed orders (scenario units)",xlabel="Recommended physical units");save(fig,"05_top_orders.png")
    pivot=sens.pivot(index="ordering_cost_assumed",columns="holding_rate_assumed",values="mean_eoq_units")
    fig,ax=plt.subplots(figsize=(6,4));im=ax.imshow(pivot,cmap="YlGnBu");ax.set_xticks(range(3),["15%","20%","30%"]);ax.set_yticks(range(3),["40","75","120"]);ax.set(xlabel="Annual holding rate",ylabel="Assumed cost per PO",title="Mean EOQ sensitivity (units)")
    for i in range(3):
        for j in range(3):ax.text(j,i,f"{pivot.iloc[i,j]:.0f}",ha="center",va="center",color="black")
    fig.colorbar(im,ax=ax,label="Mean EOQ units");save(fig,"06_eoq_sensitivity.png")
    return summary


if __name__=="__main__":print(json.dumps(build(),indent=2))
