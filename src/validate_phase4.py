"""Independent integrity, KPI arithmetic, lineage, and export reproducibility checks."""
import hashlib
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
DB = ROOT / "database/novamart_scm.db"


def main():
    before = json.loads((REPORTS/"phase4_validation.json").read_text())
    with sqlite3.connect(DB) as conn:
        conn.execute("PRAGMA foreign_keys=ON")
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert not conn.execute("PRAGMA foreign_key_check").fetchall()
        assert list(before["table_rows"].values()) == [5,100,76000,6,100,5299,5299]
        assert conn.execute("SELECT COUNT(*) FROM purchase_orders p JOIN receipts r USING(po_id) JOIN sku_supplier_map m ON p.local_sku_id=m.local_sku_id AND p.supplier_id=m.supplier_id").fetchone()[0] == 5299
        assert conn.execute("SELECT COUNT(*) FROM daily_operations d JOIN local_skus s USING(local_sku_id) JOIN locations l ON s.location_id=l.location_id").fetchone()[0] == 76000
        assert conn.execute("SELECT SUM(units_sold) FROM daily_operations").fetchone()[0] == conn.execute("SELECT SUM(x.units) FROM (SELECT local_sku_id,SUM(units_sold) AS units FROM daily_operations GROUP BY local_sku_id) x").fetchone()[0]
        spend = conn.execute("SELECT ROUND(SUM(ordered_quantity*procurement_unit_cost),2) FROM purchase_orders").fetchone()[0]
        assert spend == before["procurement_ordered_spend"]
        assert conn.execute("SELECT COUNT(*) FROM purchase_orders WHERE data_origin!='SIMULATED'").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM daily_operations WHERE data_origin!='SOURCE_SYNTHETIC_PLUS_DERIVED'").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM purchase_orders p JOIN receipts r USING(po_id) WHERE julianday(r.actual_delivery_date)-julianday(p.order_date)<0").fetchone()[0] == 0
        totals = conn.execute("SELECT COUNT(*),SUM(CASE WHEN r.actual_delivery_date<=p.expected_delivery_date THEN 1 ELSE 0 END),SUM(CASE WHEN r.actual_delivery_date>p.expected_delivery_date THEN 1 ELSE 0 END),SUM(p.ordered_quantity),SUM(r.received_quantity) FROM purchase_orders p JOIN receipts r USING(po_id)").fetchone()
        assert totals[1]+totals[2] == totals[0] == 5299 and 0 <= totals[4] <= totals[3]
        assert conn.execute("SELECT COUNT(*) FROM purchase_orders p LEFT JOIN local_skus s ON p.local_sku_id=s.local_sku_id WHERE s.local_sku_id IS NULL OR p.location_id!=s.location_id").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM receipts r LEFT JOIN purchase_orders p USING(po_id) WHERE p.po_id IS NULL").fetchone()[0] == 0
        assert conn.execute("SELECT MIN(date),MAX(date),COUNT(DISTINCT date) FROM daily_operations").fetchone() == ("2022-01-01","2024-01-30",760)
    # Save baseline hashes before rebuilding all outputs from unchanged Phase 3 CSVs.
    exports = before["export_sha256"]
    assert all(hashlib.sha256((REPORTS/name).read_bytes()).hexdigest()==digest for name,digest in exports.items())
    subprocess.run([sys.executable,str(ROOT/"src/run_phase4.py")],check=True,capture_output=True)
    after=json.loads((REPORTS/"phase4_validation.json").read_text())
    assert before==after
    print(json.dumps({"result":"PASS","foreign_keys":"PASS","joins":"PASS","date_range":"PASS","spend":"PASS","lead_time_and_percent_denominators":"PASS","lineage":"PASS","export_rebuild_hashes":"PASS","eligible_receipts":totals[0],"on_time_receipts":totals[1],"late_receipts":totals[2]},indent=2))


if __name__=="__main__":
    main()
