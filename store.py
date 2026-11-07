"""Penyimpanan hasil analisis ke SQLite berdasarkan db/schema.sql."""

import sqlite3
from pathlib import Path

from scoring import WEIGHTS

BASE = Path(__file__).resolve().parent


def connect(db_path):
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn, schema_path=None):
    schema = Path(schema_path) if schema_path else BASE / "db" / "schema.sql"
    conn.executescript(schema.read_text(encoding="utf-8"))
    conn.commit()


def save_results(conn, dataset, analysis, scores, vendor_rows):
    init_db(conn)
    conn.execute("DELETE FROM findings")
    conn.execute("DELETE FROM invoices")
    conn.execute("DELETE FROM vendors")
    risk_by_vendor = {row["vendor_id"]: row for row in vendor_rows}
    for vendor_id, vendor in dataset.vendors.items():
        row = risk_by_vendor.get(vendor_id, {})
        conn.execute(
            "INSERT INTO vendors (vendor_id, name, bank_name, bank_account, risk_score, shared_account) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (vendor_id, vendor.name, vendor.bank_name, vendor.bank_account,
             row.get("risk", 0), 1 if row.get("shared_account") else 0),
        )
    for inv in dataset.invoices:
        score_obj = scores[inv.invoice_id]
        conn.execute(
            "INSERT INTO invoices (invoice_id, invoice_no, vendor_id, po_id, invoice_date, total, score, status) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (inv.invoice_id, inv.invoice_no, inv.vendor_id, inv.po_id or None,
             inv.invoice_date.isoformat(), inv.total, score_obj.score, score_obj.status),
        )
    for finding in analysis.findings:
        conn.execute(
            "INSERT INTO findings (invoice_id, vendor_id, check_type, weight, detail) "
            "VALUES (?, ?, ?, ?, ?)",
            (finding.invoice_id, finding.vendor_id, finding.check_type,
             WEIGHTS.get(finding.check_type, 0), finding.detail),
        )
    conn.commit()


def recap_by_status(conn):
    return [dict(row) for row in conn.execute(
        "SELECT status, COUNT(*) AS jumlah_invoice, SUM(total) AS total_nilai "
        "FROM invoices GROUP BY status ORDER BY jumlah_invoice DESC")]


def recap_by_vendor(conn):
    return [dict(row) for row in conn.execute(
        "SELECT v.vendor_id, v.name, v.risk_score, COUNT(i.invoice_id) AS jumlah_invoice, "
        "SUM(CASE WHEN i.status = 'TAHAN BAYAR' THEN 1 ELSE 0 END) AS tahan_bayar, "
        "SUM(i.total) AS total_nilai FROM vendors v "
        "LEFT JOIN invoices i ON i.vendor_id = v.vendor_id "
        "GROUP BY v.vendor_id, v.name, v.risk_score ORDER BY v.risk_score DESC")]


def findings_by_type(conn):
    return [dict(row) for row in conn.execute(
        "SELECT check_type, COUNT(*) AS jumlah_temuan FROM findings "
        "WHERE invoice_id IS NOT NULL GROUP BY check_type ORDER BY jumlah_temuan DESC")]


def main():
    import argparse

    import checks
    import loader
    import scoring

    parser = argparse.ArgumentParser(description="Simpan hasil analisis ke SQLite")
    parser.add_argument("--samples", default="samples")
    parser.add_argument("--db", default="invoice_fraud.db")
    args = parser.parse_args()

    dataset = loader.load_dataset(args.samples)
    analysis = checks.run_checks(dataset)
    scores = scoring.score_invoices(dataset, analysis)
    vendor_rows = scoring.vendor_risk(dataset, analysis, scores)
    conn = connect(args.db)
    try:
        save_results(conn, dataset, analysis, scores, vendor_rows)
        print(f"Tersimpan ke {args.db}: {len(dataset.invoices)} invoice, "
              f"{len(analysis.findings)} temuan.")
        for row in recap_by_status(conn):
            print(f"  {row['status']}: {row['jumlah_invoice']} invoice")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
