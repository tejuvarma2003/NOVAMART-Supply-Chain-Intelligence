"""Build SQLite with explicit schema, execute SQL files, export selected results."""
import csv
import hashlib
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "database/novamart_scm.db"
INPUT = ROOT / "data/processed"
REPORTS = ROOT / "reports"
ORDER = ["locations", "local_skus", "daily_operations", "suppliers", "sku_supplier_map", "purchase_orders", "receipts"]
EXPECTED = [5, 100, 76000, 6, 100, 5299, 5299]


def statements(path):
    buffer = ""
    for line in path.read_text().splitlines(keepends=True):
        buffer += line
        if sqlite3.complete_statement(buffer):
            if buffer.strip():
                yield buffer
            buffer = ""
    assert not buffer.strip(), path


def export(conn, sql, filename):
    cursor = conn.execute(sql)
    rows = cursor.fetchall()
    path = REPORTS / filename
    with path.open("w", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow([col[0] for col in cursor.description])
        writer.writerows(rows)
    return len(rows)


def main():
    DB.unlink(missing_ok=True)
    conn = sqlite3.connect(DB)
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        conn.executescript((ROOT / "database/schema.sql").read_text())
        with conn:
            for name, expected in zip(ORDER, EXPECTED):
                with (INPUT/f"{name}.csv").open(newline="") as stream:
                    reader = csv.DictReader(stream)
                    cols = reader.fieldnames
                    sql = f"INSERT INTO {name} ({','.join(cols)}) VALUES ({','.join('?' for _ in cols)})"
                    conn.executemany(sql, ([row[c] for c in cols] for row in reader))
                assert conn.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0] == expected
        assert not conn.execute("PRAGMA foreign_key_check").fetchall()
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        all_queries = {}
        for path in sorted((ROOT/"sql").glob("0[1-6]_*.sql")):
            queries = list(statements(path))
            for query in queries:
                conn.execute(query).fetchall()  # execute every analytical statement
            all_queries[path.name] = queries
        selection = [
            ("02_demand_analysis.sql", 0, "demand_summary.csv"),
            ("03_inventory_analysis.sql", 4, "inventory_summary.csv"),
            ("04_procurement_analysis.sql", 1, "procurement_summary.csv"),
            ("05_supplier_analysis.sql", 0, "supplier_performance.csv"),
            ("06_management_queries.sql", 0, "supply_chain_exceptions.csv"),
        ]
        export_counts = {out:export(conn, all_queries[file][index], out) for file,index,out in selection}
        summary = {
            "foreign_keys_enabled": conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1,
            "integrity_check": conn.execute("PRAGMA integrity_check").fetchone()[0],
            "foreign_key_violations": len(conn.execute("PRAGMA foreign_key_check").fetchall()),
            "table_rows": {name:conn.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0] for name in ORDER},
            "daily_date_range": conn.execute("SELECT MIN(date),MAX(date),COUNT(DISTINCT date) FROM daily_operations").fetchone(),
            "procurement_ordered_spend": conn.execute("SELECT ROUND(SUM(ordered_quantity*procurement_unit_cost),2) FROM purchase_orders").fetchone()[0],
            "export_rows": export_counts,
            "export_sha256": {name:hashlib.sha256((REPORTS/name).read_bytes()).hexdigest() for name in export_counts},
        }
        (REPORTS/"phase4_validation.json").write_text(json.dumps(summary, indent=2)+"\n")
        print(json.dumps(summary, indent=2))
    finally:
        conn.close()


if __name__ == "__main__":
    main()
