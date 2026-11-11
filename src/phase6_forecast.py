"""Direct 14-day global forecasting with chronological, nonoverlapping holdouts."""
from pathlib import Path
import json
import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

ROOT=Path(__file__).resolve().parents[1]
REPORTS=ROOT/"reports"; IMAGES=ROOT/"images/forecasting"; MODELS=ROOT/"models"
NUM=["horizon_day","last_sales","lag_7","lag_14","lag_28","mean_7","mean_14","mean_28","std_7","std_28","target_dow","target_month","target_weekend"]
CAT=["local_sku_id","location_id","category"]
FEATURES=NUM+CAT
TRAIN_END=pd.Timestamp("2023-08-31")
VAL_START=pd.Timestamp("2023-09-01")
TEST_START=pd.Timestamp("2023-11-11")
VAL_ORIGINS=pd.date_range("2023-09-01",periods=5,freq="14D")
TEST_ORIGINS=pd.date_range("2023-11-11",periods=5,freq="14D")


def load_panel():
    d=pd.read_csv(ROOT/"data/processed/daily_operations.csv",parse_dates=["date"])
    s=pd.read_csv(ROOT/"data/processed/local_skus.csv")
    d=d.merge(s[["local_sku_id","category"]],on="local_sku_id",validate="many_to_one")
    d=d.sort_values(["local_sku_id","date"])
    assert len(d)==76000 and d.local_sku_id.nunique()==100
    return d


def make_rows(d, origins, future=False):
    """Each row predicts one horizon day from a frozen 28-day history at origin."""
    records=[]
    for sku,g in d.groupby("local_sku_id",sort=True):
        g=g.set_index("date").sort_index()
        for origin in origins:
            history=g.loc[:origin,"units_sold"]
            if len(history)<28 or history.index[-1]!=origin: continue
            tail=history.iloc[-28:].to_numpy(dtype=float)
            feats={"local_sku_id":sku,"location_id":g.location_id.iloc[0],"category":g.category.iloc[0],
                   "last_sales":tail[-1],"lag_7":tail[-7],"lag_14":tail[-14],"lag_28":tail[-28],
                   "mean_7":tail[-7:].mean(),"mean_14":tail[-14:].mean(),"mean_28":tail.mean(),
                   "std_7":tail[-7:].std(ddof=0),"std_28":tail.std(ddof=0)}
            for h in range(1,15):
                date=origin+pd.Timedelta(days=h)
                if not future and date not in g.index:continue
                records.append({**feats,"origin_date":origin,"forecast_date":date,"horizon_day":h,
                                "target_dow":date.dayofweek,"target_month":date.month,
                                "target_weekend":int(date.dayofweek>=5),
                                "actual":np.nan if future else float(g.at[date,"units_sold"])})
    return pd.DataFrame(records)


def metrics(y,p):
    y=np.asarray(y,dtype=float);p=np.asarray(p,dtype=float)
    err=y-p
    return {"MAE":float(np.mean(np.abs(err))),"RMSE":float(np.sqrt(np.mean(err**2))),
            "WAPE_pct":float(100*np.sum(np.abs(err))/np.sum(np.abs(y)))}


def model(name):
    if name=="Ridge":
        pre=ColumnTransformer([("numeric",StandardScaler(),NUM),
                               ("categorical",OneHotEncoder(handle_unknown="ignore"),CAT)])
        return Pipeline([("features",pre),("regressor",Ridge(alpha=100.0))])
    # Numeric identities are codes only for tree splits; no ordinal business meaning.
    return HistGradientBoostingRegressor(max_iter=120,max_leaf_nodes=15,learning_rate=.07,
                                         min_samples_leaf=60,l2_regularization=10,random_state=42)


def tree_frame(x, categories):
    f=x[NUM].copy()
    for c in CAT:f[c]=pd.Categorical(x[c],categories=categories[c]).codes
    assert (f[CAT]>=0).all().all()
    return f


def evaluate(frame, label, fitted, cats):
    result=frame[["origin_date","forecast_date","horizon_day","location_id","local_sku_id","category","actual"]].copy()
    result["naive_last"]=frame.last_sales.to_numpy()
    result["mean_7"]=frame.mean_7.to_numpy()
    result["mean_28"]=frame.mean_28.to_numpy()
    result["Ridge"]=np.maximum(0,fitted["Ridge"].predict(frame[FEATURES]))
    result["HistGradientBoosting"]=np.maximum(0,fitted["HistGradientBoosting"].predict(tree_frame(frame,cats)))
    result["split"]=label
    return result


def main():
    IMAGES.mkdir(parents=True,exist_ok=True);MODELS.mkdir(parents=True,exist_ok=True)
    d=load_panel(); dates=pd.date_range(d.date.min()+pd.Timedelta(days=27),TRAIN_END-pd.Timedelta(days=14),freq="14D")
    train=make_rows(d,dates)
    val=make_rows(d,VAL_ORIGINS)
    test=make_rows(d,TEST_ORIGINS)
    assert train.forecast_date.max()<=TRAIN_END and val.origin_date.min()==VAL_START
    assert val.forecast_date.max()<TEST_START and test.forecast_date.max()<=d.date.max()
    assert len(val)==len(test)==7000
    cats={c:sorted(d[c].unique()) for c in CAT}
    fitted={"Ridge":model("Ridge").fit(train[FEATURES],train.actual),
            "HistGradientBoosting":model("HistGradientBoosting").fit(tree_frame(train,cats),train.actual)}
    validation=evaluate(val,"validation",fitted,cats)
    testing=evaluate(test,"test",fitted,cats)
    choices=["naive_last","mean_7","mean_28","Ridge","HistGradientBoosting"]
    rows=[]
    for split,preds in [("validation",validation),("test",testing)]:
        for name in choices:rows.append({"split":split,"model":name,**metrics(preds.actual,preds[name])})
    comparison=pd.DataFrame(rows)
    comparison.to_csv(REPORTS/"forecast_model_comparison.csv",index=False,float_format="%.6f")
    validation_ranking=comparison.query("split=='validation'").sort_values(["WAPE_pct","MAE","model"])
    best=validation_ranking.iloc[0]["model"]
    ridge_wape=float(validation_ranking.set_index("model").loc["Ridge","WAPE_pct"])
    # Predeclared parsimony margin: retain interpretable Ridge when within one
    # percentage point WAPE of the best validation candidate.
    if ridge_wape-float(validation_ranking.iloc[0].WAPE_pct)<=1.0:best="Ridge"
    # Test set is untouched for model selection. Baselines need no fitting.
    testing["prediction"]=testing[best]
    all_oos=pd.concat([validation,testing],ignore_index=True)
    all_oos["prediction"]=all_oos[best]
    all_oos["error"]=all_oos.actual-all_oos.prediction
    all_oos.to_csv(REPORTS/"forecast_holdout_predictions.csv",index=False,float_format="%.6f",date_format="%Y-%m-%d")
    grouped=[]
    for sku,g in all_oos.groupby("local_sku_id"):
        grouped.append({"local_sku_id":sku,"location_id":g.location_id.iloc[0],"category":g.category.iloc[0],
                        "oos_rows":len(g),"forecast_mae":np.abs(g.error).mean(),
                        "forecast_rmse":np.sqrt(np.mean(g.error**2)),"forecast_error_std":g.error.std(ddof=0),
                        "WAPE_pct":100*np.abs(g.error).sum()/g.actual.sum() if g.actual.sum()>0 else np.nan})
    errors=pd.DataFrame(grouped).sort_values("local_sku_id")
    errors.to_csv(REPORTS/"forecast_error_by_sku.csv",index=False,float_format="%.6f")
    category=[];location=[]
    for field,target in [("category",category),("location_id",location)]:
        for key,g in testing.groupby(field):target.append({field:key,"n":len(g),**metrics(g.actual,g.prediction)})
    pd.DataFrame(category).to_csv(REPORTS/"forecast_by_category.csv",index=False,float_format="%.6f")
    pd.DataFrame(location).to_csv(REPORTS/"forecast_by_location.csv",index=False,float_format="%.6f")

    # Refit selected ML candidate after evaluation; baselines use the latest history.
    latest=d.date.max(); full_origins=pd.date_range(d.date.min()+pd.Timedelta(days=27),latest-pd.Timedelta(days=14),freq="14D")
    full=make_rows(d,full_origins)
    forward=make_rows(d,[latest],future=True)
    if best in fitted:
        selected=model(best)
        if best=="Ridge":selected.fit(full[FEATURES],full.actual);p=selected.predict(forward[FEATURES])
        else:selected.fit(tree_frame(full,cats),full.actual);p=selected.predict(tree_frame(forward,cats))
        joblib.dump({"model":selected,"name":best,"categories":cats,"features":FEATURES},MODELS/"selected_forecaster.joblib")
    else:
        p=forward[{"naive_last":"last_sales","mean_7":"mean_7","mean_28":"mean_28"}[best]].to_numpy()
        (MODELS/"selected_baseline.json").write_text(json.dumps({"model":best,"history":"all available through 2024-01-30"},indent=2)+"\n")
    future=forward[["forecast_date","location_id","local_sku_id"]].copy()
    future["predicted_units"]=np.maximum(0,p)
    future["model"]=best;future["data_origin"]="MODEL_FORECAST_FROM_SOURCE_SYNTHETIC"
    future.to_csv(REPORTS/"demand_forecast_14d.csv",index=False,float_format="%.6f",date_format="%Y-%m-%d")
    summary=future.groupby(["location_id","local_sku_id"],as_index=False).predicted_units.agg(forecast_14d_units="sum",average_forecast_daily_units="mean")
    summary.to_csv(REPORTS/"demand_forecast_14d_summary.csv",index=False,float_format="%.6f")

    plt.rcParams.update({"font.size":10,"axes.spines.top":False,"axes.spines.right":False})
    fig,ax=plt.subplots(figsize=(8,4));v=comparison[comparison.split.eq("test")]
    ax.barh(v.model,v.WAPE_pct,color=["#168f8b" if m==best else "#8a9bab" for m in v.model]);ax.invert_yaxis()
    ax.set(xlabel="Test WAPE (%)",title="14-day direct forecast comparison (chronological holdout)")
    fig.tight_layout();fig.savefig(IMAGES/"01_model_comparison.png",dpi=160);plt.close(fig)
    sku=errors.sort_values("WAPE_pct").iloc[len(errors)//2].local_sku_id
    g=testing[testing.local_sku_id.eq(sku)].sort_values("forecast_date")
    fig,ax=plt.subplots(figsize=(10,4));ax.plot(g.forecast_date,g.actual,label="Actual",color="#24364b");ax.plot(g.forecast_date,g[best],label="Forecast",color="#e77e65")
    ax.set(title=f"Representative local SKU {sku}: test blocks",xlabel="Date",ylabel="Units per day");ax.legend();fig.autofmt_xdate();fig.tight_layout();fig.savefig(IMAGES/"02_actual_vs_forecast.png",dpi=160);plt.close(fig)
    catplot=pd.DataFrame(category).sort_values("WAPE_pct")
    fig,ax=plt.subplots(figsize=(8,4));ax.barh(catplot.category,catplot.WAPE_pct,color="#168f8b");ax.set(title="Test WAPE by category",xlabel="WAPE (%)");fig.tight_layout();fig.savefig(IMAGES/"03_category_wape.png",dpi=160);plt.close(fig)
    variability=pd.read_csv(REPORTS/"sku_demand_profile.csv")[["local_sku_id","cv_daily_units"]]
    diagnostic=errors.merge(variability,on="local_sku_id",validate="one_to_one")
    fig,ax=plt.subplots(figsize=(7,4));ax.scatter(diagnostic.cv_daily_units,diagnostic.WAPE_pct,color="#168f8b",alpha=.7)
    ax.set(title="Out-of-sample SKU WAPE vs historical sales variability",xlabel="Daily sales coefficient of variation",ylabel="OOS WAPE (%)");fig.tight_layout();fig.savefig(IMAGES/"04_error_vs_variability.png",dpi=160);plt.close(fig)
    example=future[future.local_sku_id.eq(sku)]
    fig,ax=plt.subplots(figsize=(8,4));ax.plot(example.forecast_date,example.predicted_units,marker="o",color="#168f8b")
    ax.set(title=f"Forward 14-day forecast: {sku}",xlabel="Future date",ylabel="Predicted units per day");fig.autofmt_xdate();fig.tight_layout();fig.savefig(IMAGES/"05_forward_example.png",dpi=160);plt.close(fig)
    manifest={"train_origin_min":str(train.origin_date.min().date()),"train_origin_max":str(train.origin_date.max().date()),
              "train_target_min":str(train.forecast_date.min().date()),"train_target_max":str(train.forecast_date.max().date()),
              "validation_origin_dates":[str(x.date()) for x in VAL_ORIGINS],"validation_target_min":str(val.forecast_date.min().date()),"validation_target_max":str(val.forecast_date.max().date()),
              "test_origin_dates":[str(x.date()) for x in TEST_ORIGINS],"test_target_min":str(test.forecast_date.min().date()),"test_target_max":str(test.forecast_date.max().date()),
              "train_rows":len(train),"validation_rows":len(val),"test_rows":len(test),"selected_model":best,
              "forward_start":str(future.forecast_date.min().date()),"forward_end":str(future.forecast_date.max().date()),"forward_rows":len(future),
              "forward_total_units":round(float(future.predicted_units.sum()),3)}
    (REPORTS/"phase6_manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    print(json.dumps(manifest,indent=2));print(comparison.to_string(index=False))


if __name__=="__main__":main()
