"""Prepare source-derived daily tables and an explicitly simulated procurement scenario."""
from pathlib import Path
import hashlib
import json
import zipfile

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw/atomicd_retail_inventory_v8.zip"
OUT = ROOT / "data/processed"
SEED = 31027

RENAME = {
    "Date": "date", "Store ID": "original_store_id", "Product ID": "original_product_id",
    "Category": "category", "Region": "region", "Inventory Level": "inventory_units",
    "Units Sold": "units_sold", "Units Ordered": "units_ordered_source",
    "Price": "listed_price", "Discount": "discount_source", "Weather Condition": "weather_condition",
    "Promotion": "promotion_flag", "Competitor Pricing": "competitor_price",
    "Seasonality": "seasonality_label", "Epidemic": "epidemic_flag",
    "Demand": "estimated_demand_source",
}


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(RAW) as archive:
        with archive.open("sales_data.csv") as stream:
            source = pd.read_csv(stream)
    assert list(source.columns) == list(RENAME), "Unexpected source version/columns"
    assert not source.isna().any().any() and not source.duplicated().any()
    d = source.rename(columns=RENAME).copy()
    d["date"] = pd.to_datetime(d["date"], format="%Y-%m-%d", errors="raise")
    assert not d.duplicated(["date", "original_store_id", "original_product_id"]).any()
    assert d["original_store_id"].str.fullmatch(r"S\d{3}").all()
    assert d["original_product_id"].str.fullmatch(r"P\d{4}").all()
    for col in ["inventory_units", "units_sold", "units_ordered_source", "estimated_demand_source", "listed_price", "competitor_price"]:
        assert d[col].ge(0).all(), col
    assert d["listed_price"].gt(0).all() and d["competitor_price"].gt(0).all()
    assert d["discount_source"].between(0, 100).all()
    assert d["promotion_flag"].isin([0, 1]).all() and d["epidemic_flag"].isin([0, 1]).all()
    assert d.groupby("original_store_id")["region"].nunique().eq(1).all()
    assert d.groupby(["original_store_id", "original_product_id"])["category"].nunique().eq(1).all()

    d["location_id"] = d["original_store_id"]
    d["local_sku_id"] = d["original_store_id"] + "_" + d["original_product_id"]
    locations = d[["location_id", "original_store_id", "region"]].drop_duplicates().sort_values("location_id").reset_index(drop=True)
    locations["location_name"] = "NOVAMART Location " + locations["original_store_id"]
    skus = d[["local_sku_id", "original_product_id", "location_id", "category"]].drop_duplicates().sort_values("local_sku_id").reset_index(drop=True)

    dt = d["date"]
    d["year"] = dt.dt.year
    d["quarter"] = dt.dt.quarter
    d["month"] = dt.dt.month
    d["month_name"] = dt.dt.month_name()
    d["week_of_year"] = dt.dt.isocalendar().week.astype(int)
    d["day_of_week"] = dt.dt.dayofweek
    d["day_name"] = dt.dt.day_name()
    d["is_weekend"] = d["day_of_week"].ge(5).astype(int)
    d["data_origin"] = "SOURCE_SYNTHETIC_PLUS_DERIVED"
    d = d.drop(columns=["original_store_id", "original_product_id", "category", "region"])
    d = d.sort_values(["date", "location_id", "local_sku_id"]).reset_index(drop=True)
    assert len(skus) == 100 and len(locations) == 5
    assert d.groupby("local_sku_id")["date"].nunique().eq(760).all()
    assert not d.duplicated(["date", "local_sku_id"]).any()

    # Fictional supplier parameters and region are scenario inputs, never measured KPIs.
    rng = np.random.default_rng(SEED)
    supplier_defs = [
        ("SUP-01", "Northstar Goods", "North", 5, 1.0, .64, .97),
        ("SUP-02", "Cedar Wholesale", "South", 7, 1.5, .67, .94),
        ("SUP-03", "Harbor Supply", "East", 9, 2.0, .61, .91),
        ("SUP-04", "Summit Distribution", "West", 6, 1.0, .69, .96),
        ("SUP-05", "Pioneer Trading", "North", 11, 2.5, .59, .88),
        ("SUP-06", "Willow Merchants", "South", 8, 1.5, .66, .93),
    ]
    suppliers = pd.DataFrame(supplier_defs, columns=["supplier_id", "supplier_name", "supplier_region", "base_lead_time_days", "lead_time_variability_days", "unit_cost_factor", "fulfillment_probability_assumption"])
    suppliers["data_origin"] = "SIMULATED"
    # Assign one primary supplier per local SKU by a stable index. Same-source Product IDs
    # at different stores are separate local SKUs, so sourcing can differ.
    # Initial listed price is known before the first simulated PO; never use
    # the final price from the end of history in earlier sourcing decisions.
    initial_prices = d.sort_values("date").groupby("local_sku_id", sort=True).head(1).set_index("local_sku_id")["listed_price"]
    mapping = []
    for i, row in enumerate(skus.itertuples(index=False)):
        supplier = supplier_defs[i % len(supplier_defs)]
        mapping.append((row.local_sku_id, supplier[0], 1, supplier[3], round(float(initial_prices[row.local_sku_id]) * supplier[5], 2), "SIMULATED"))
    sourcing = pd.DataFrame(mapping, columns=["local_sku_id", "supplier_id", "primary_supplier_flag", "expected_lead_time_days", "procurement_unit_cost", "data_origin"])

    # Every 14th day after a 28-day warmup, review each SKU. Only preceding 28
    # observed sales and the inventory snapshot at the decision date are consulted.
    # Same-day sales/demand and future observations are never inputs to the policy.
    po_rows, receipt_rows = [], []
    supplier_by_id = suppliers.set_index("supplier_id")
    source_by_sku = d.sort_values(["local_sku_id", "date"]).groupby("local_sku_id", sort=True)
    source_by_map = sourcing.set_index("local_sku_id")
    for sku, frame in source_by_sku:
        frame = frame.reset_index(drop=True)
        relation = source_by_map.loc[sku]
        supplier = supplier_by_id.loc[relation.supplier_id]
        for idx in range(28, len(frame), 14):
            past_daily = float(frame.loc[idx-28:idx-1, "units_sold"].mean())
            on_hand = int(frame.loc[idx, "inventory_units"])
            # 21 days is a documented scenario target, not a fitted optimization.
            qty = max(0, int(np.ceil(21 * past_daily - on_hand)))
            if qty == 0:
                continue
            order_date = frame.loc[idx, "date"]
            expected_date = order_date + pd.Timedelta(days=int(relation.expected_lead_time_days))
            # Draw actual transit around supplier's assumed distribution. This
            # simulates outcomes but does not attempt inventory reconciliation.
            variance = int(np.rint(rng.normal(0, float(supplier.lead_time_variability_days))))
            actual_days = max(1, int(relation.expected_lead_time_days) + variance)
            actual_date = order_date + pd.Timedelta(days=actual_days)
            fulfilled = rng.random() < float(supplier.fulfillment_probability_assumption)
            received = qty if fulfilled else int(np.floor(qty * rng.uniform(.75, .99)))
            po_id = f"PO-{len(po_rows)+1:06d}"
            po_rows.append((po_id, relation.supplier_id, sku, frame.loc[idx, "location_id"], order_date, qty, expected_date, relation.procurement_unit_cost, "RECEIVED" if received == qty else "PARTIALLY_RECEIVED", "SIMULATED"))
            receipt_rows.append((f"RC-{len(receipt_rows)+1:06d}", po_id, actual_date, received, "COMPLETE" if received == qty else "PARTIAL", "SIMULATED"))
    purchase_orders = pd.DataFrame(po_rows, columns=["po_id", "supplier_id", "local_sku_id", "location_id", "order_date", "ordered_quantity", "expected_delivery_date", "procurement_unit_cost", "po_status", "data_origin"])
    receipts = pd.DataFrame(receipt_rows, columns=["receipt_id", "po_id", "actual_delivery_date", "received_quantity", "delivery_status", "data_origin"])

    tables = {"locations": locations, "local_skus": skus, "daily_operations": d,
              "suppliers": suppliers, "sku_supplier_map": sourcing,
              "purchase_orders": purchase_orders, "receipts": receipts}
    for name, frame in tables.items():
        frame.to_csv(OUT / f"{name}.csv", index=False, date_format="%Y-%m-%d", lineterminator="\n")
    manifest = {"seed": SEED, "raw_sha256": hashlib.sha256(RAW.read_bytes()).hexdigest(),
                "tables": {name: {"rows": len(frame), "sha256": hashlib.sha256((OUT/f"{name}.csv").read_bytes()).hexdigest()} for name, frame in tables.items()}}
    (OUT / "phase3_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({name:len(frame) for name,frame in tables.items()}, indent=2))


if __name__ == "__main__":
    build()
