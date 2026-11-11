"""Reproducible descriptive EDA; no forecasting or inventory optimization."""
from pathlib import Path
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/processed"
REPORTS = ROOT / "reports"
IMAGES = ROOT / "images/eda"
NAVY, TEAL, CORAL = "#24364b", "#168f8b", "#e77e65"


def load():
    daily = pd.read_csv(DATA/"daily_operations.csv", parse_dates=["date"])
    skus = pd.read_csv(DATA/"local_skus.csv")
    locations = pd.read_csv(DATA/"locations.csv")
    po = pd.read_csv(DATA/"purchase_orders.csv", parse_dates=["order_date","expected_delivery_date"])
    receipts = pd.read_csv(DATA/"receipts.csv", parse_dates=["actual_delivery_date"])
    suppliers = pd.read_csv(DATA/"suppliers.csv")
    return daily,skus,locations,po,receipts,suppliers


def save(fig, name):
    fig.tight_layout()
    fig.savefig(IMAGES/name, dpi=165, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def run():
    IMAGES.mkdir(parents=True,exist_ok=True)
    d, skus, loc, po, receipts, suppliers = load()
    assert len(d)==76000 and d.local_sku_id.nunique()==100 and d.date.nunique()==760
    assert not d.isna().any().any() and not d.duplicated(["date","local_sku_id"]).any()
    assert d.data_origin.eq("SOURCE_SYNTHETIC_PLUS_DERIVED").all()
    assert po.data_origin.eq("SIMULATED").all() and receipts.data_origin.eq("SIMULATED").all()
    e = d.merge(skus[["local_sku_id","category"]],on="local_sku_id",validate="many_to_one")
    assert len(e)==len(d)
    sku = e.groupby(["local_sku_id","location_id","category"],as_index=False).agg(
        days=("date","size"), total_units=("units_sold","sum"), mean_daily_units=("units_sold","mean"),
        sd_daily_units=("units_sold","std"), zero_sales_days=("units_sold",lambda x:int(x.eq(0).sum())),
        zero_inventory_days=("inventory_units",lambda x:int(x.eq(0).sum())),
        avg_inventory_units=("inventory_units","mean"))
    sku["cv_daily_units"] = sku.sd_daily_units/sku.mean_daily_units.replace(0,np.nan)
    sku["zero_sales_rate"] = sku.zero_sales_days/sku.days
    sku.to_csv(REPORTS/"sku_demand_profile.csv",index=False,float_format="%.6f")

    latest_date=d.date.max()
    current = e[e.date.eq(latest_date)][["local_sku_id","location_id","category","inventory_units"]].copy()
    recent = d[d.date.gt(latest_date-pd.Timedelta(days=28))].groupby("local_sku_id").units_sold.sum().div(28).rename("avg_daily_units_28d")
    inv=current.merge(recent,on="local_sku_id",validate="one_to_one")
    inv["coverage_days_proxy"] = inv.inventory_units/inv.avg_daily_units_28d.replace(0,np.nan)
    inv.to_csv(REPORTS/"inventory_eda_summary.csv",index=False,float_format="%.6f")

    events=po.merge(receipts,on="po_id",validate="one_to_one").merge(suppliers[["supplier_id","supplier_name"]],on="supplier_id",validate="many_to_one")
    assert len(events)==len(po)==len(receipts)
    events["expected_lead_days"]=(events.expected_delivery_date-events.order_date).dt.days
    events["actual_lead_days"]=(events.actual_delivery_date-events.order_date).dt.days
    events["delay_days"]=(events.actual_delivery_date-events.expected_delivery_date).dt.days
    events["ordered_commitment"]=events.ordered_quantity*events.procurement_unit_cost
    events["on_time"]=events.delay_days.le(0)
    supp=events.groupby(["supplier_id","supplier_name"],as_index=False).agg(
        purchase_orders=("po_id","size"), ordered_commitment=("ordered_commitment","sum"),
        mean_actual_lead_days=("actual_lead_days","mean"), lead_sd_days=("actual_lead_days",lambda x:x.std(ddof=0)),
        on_time_pct=("on_time",lambda x:100*x.mean()), late_pct=("on_time",lambda x:100*(~x).mean()),
        ordered_units=("ordered_quantity","sum"),received_units=("received_quantity","sum"),
        mean_positive_delay_all_days=("delay_days",lambda x:x.clip(lower=0).mean()))
    supp["receipt_fill_pct"]=100*supp.received_units/supp.ordered_units
    supp["data_origin"]="SIMULATED"
    supp.to_csv(REPORTS/"supplier_eda_summary.csv",index=False,float_format="%.6f")

    plt.rcParams.update({"font.size":10,"axes.spines.top":False,"axes.spines.right":False,"axes.labelcolor":NAVY,"text.color":NAVY})
    monthly=d.groupby(d.date.dt.to_period("M")).units_sold.sum()
    daily_total=d.groupby("date").units_sold.sum()
    rolling=daily_total.rolling(28,min_periods=28).mean()
    fig,ax=plt.subplots(figsize=(11,4)); ax.plot(rolling.index,rolling,color=TEAL,lw=2)
    ax.set(title="Observed units sold: 28-day trailing mean",xlabel="Date",ylabel="Units per day (all local SKUs)"); save(fig,"01_sales_trend.png")

    fig,ax=plt.subplots(figsize=(11,4)); ax.bar(monthly.index.astype(str),monthly.values,color=TEAL)
    ax.tick_params(axis="x",rotation=70); ax.set(title="Monthly units sold (January 2024 has 30 days)",xlabel="Month",ylabel="Units sold"); save(fig,"02_monthly_sales.png")

    dow=d.groupby("day_of_week").units_sold.mean().reindex(range(7))
    fig,ax=plt.subplots(figsize=(8,4)); ax.bar(["Mon","Tue","Wed","Thu","Fri","Sat","Sun"],dow.values,color=TEAL)
    ax.set(title="Average units sold per SKU-day by weekday",xlabel="Day of week",ylabel="Mean units sold"); save(fig,"03_weekday_sales.png")

    cat=e.groupby("category").units_sold.sum().sort_values()
    place=d.groupby("location_id").units_sold.sum().sort_values()
    fig,axes=plt.subplots(1,2,figsize=(11,4)); axes[0].barh(cat.index,cat.values,color=TEAL);axes[1].barh(place.index,place.values,color=CORAL)
    axes[0].set(title="Units sold by category",xlabel="Units sold");axes[1].set(title="Units sold by location",xlabel="Units sold")
    save(fig,"04_category_location_sales.png")

    fig,ax=plt.subplots(figsize=(8,4)); ax.hist(sku.cv_daily_units,bins=18,color=TEAL,edgecolor="white")
    ax.set(title="Local-SKU daily sales variability",xlabel="Coefficient of variation (daily units sold)",ylabel="Number of local SKUs");save(fig,"05_sku_variability.png")

    fig,axes=plt.subplots(1,2,figsize=(11,4));axes[0].hist(d.inventory_units,bins=40,color=TEAL,edgecolor="white")
    axes[0].set(xlabel="Inventory units per snapshot",ylabel="SKU-day observations",title="Inventory snapshot distribution")
    axes[1].hist(inv.coverage_days_proxy,bins=25,color=CORAL,edgecolor="white")
    axes[1].axvline(7,color=NAVY,ls="--",label="Illustrative 7-day screen");axes[1].legend()
    axes[1].set(xlabel="Coverage days (28-day sales proxy)",ylabel="Local SKUs",title="Latest inventory coverage")
    save(fig,"06_inventory_distribution_coverage.png")

    prom=d.groupby("promotion_flag").units_sold.agg(["mean","size"])
    discounts=d.groupby("discount_source").units_sold.mean()
    fig,axes=plt.subplots(1,2,figsize=(10,4)); axes[0].bar(["No flag","Promotion"],prom["mean"],color=[NAVY,TEAL]);axes[0].set(title="Association with promotion flag",ylabel="Mean units sold per SKU-day")
    axes[1].plot(discounts.index,discounts.values,"o-",color=CORAL);axes[1].set(title="Sales by listed discount",xlabel="Discount source value (%)",ylabel="Mean units sold per SKU-day")
    save(fig,"07_promotion_discount_sales.png")

    fig,axes=plt.subplots(1,2,figsize=(11,4));axes[0].barh(supp.supplier_id,supp.on_time_pct,color=TEAL)
    axes[0].set(xlim=(0,100),title="SIMULATED supplier on-time receipts",xlabel="On-time receipts (%)")
    axes[1].errorbar(supp.mean_actual_lead_days,supp.supplier_id,xerr=supp.lead_sd_days,fmt="o",color=CORAL,capsize=3)
    axes[1].set(title="SIMULATED lead time (mean ± population SD)",xlabel="Actual lead days")
    save(fig,"08_simulated_supplier_delivery.png")

    numeric=["units_sold","inventory_units","listed_price","discount_source","promotion_flag","estimated_demand_source"]
    corr=d[numeric].corr()
    fig,ax=plt.subplots(figsize=(7,5));im=ax.imshow(corr,vmin=-1,vmax=1,cmap="BrBG")
    ax.set_xticks(range(len(numeric)),numeric,rotation=45,ha="right");ax.set_yticks(range(len(numeric)),numeric)
    for i in range(len(numeric)):
        for j in range(len(numeric)):ax.text(j,i,f"{corr.iloc[i,j]:.2f}",ha="center",va="center",fontsize=8)
    fig.colorbar(im,ax=ax,label="Pearson correlation")
    ax.set(title="Source synthetic SKU-day correlations (not causal)");save(fig,"09_source_correlations.png")

    metrics={
        "operational_rows":len(d),"local_skus":len(sku),"date_min":str(d.date.min().date()),"date_max":str(latest_date.date()),
        "total_units_sold":int(d.units_sold.sum()),"zero_inventory_days":int(d.inventory_units.eq(0).sum()),
        "zero_sales_days":int(d.units_sold.eq(0).sum()),"latest_inventory_units":int(inv.inventory_units.sum()),
        "below_7_day_coverage_skus":int(inv.coverage_days_proxy.lt(7).sum()),
        "coverage_median_days":round(float(inv.coverage_days_proxy.median()),3),
        "sku_cv_median":round(float(sku.cv_daily_units.median()),3),
        "sku_cv_min":round(float(sku.cv_daily_units.min()),3),"sku_cv_max":round(float(sku.cv_daily_units.max()),3),
        "top_10_sku_sales_share":round(float(sku.nlargest(10,"total_units").total_units.sum()/d.units_sold.sum()),4),
        "weekday_mean_sales":{str(k):round(float(v),3) for k,v in dow.items()},
        "category_units":{k:int(v) for k,v in cat.items()},"location_units":{k:int(v) for k,v in place.items()},
        "promotion_mean_units":{str(k):round(float(v),3) for k,v in prom["mean"].items()},
        "discount_mean_units":{str(k):round(float(v),3) for k,v in discounts.items()},
        "listed_price_median":float(d.listed_price.median()),
        "correlations_with_sales":{k:round(float(v),3) for k,v in corr.units_sold.items()},
        "simulated_po_count":len(po),"simulated_ordered_commitment":round(float(events.ordered_commitment.sum()),2),
        "simulated_full_receipts":int(receipts.delivery_status.eq("COMPLETE").sum()),
        "simulated_partial_receipts":int(receipts.delivery_status.eq("PARTIAL").sum()),
        "simulated_ontime_count":int(events.on_time.sum()),"simulated_late_count":int((~events.on_time).sum()),
        "simulated_actual_lead_min":int(events.actual_lead_days.min()),"simulated_actual_lead_max":int(events.actual_lead_days.max()),
        "simulated_monthly_po_counts":{str(k):int(v) for k,v in po.groupby(po.order_date.dt.to_period("M")).size().items()},
    }
    (REPORTS/"phase5_metrics.json").write_text(json.dumps(metrics,indent=2)+"\n")
    return metrics


if __name__=="__main__":
    print(json.dumps(run(),indent=2))
