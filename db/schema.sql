CREATE TABLE IF NOT EXISTS vendors (
    vendor_id     TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    bank_name     TEXT,
    bank_account  TEXT,
    risk_score    INTEGER DEFAULT 0,
    shared_account INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS invoices (
    invoice_id   TEXT PRIMARY KEY,
    invoice_no   TEXT NOT NULL,
    vendor_id    TEXT NOT NULL REFERENCES vendors (vendor_id),
    po_id        TEXT,
    invoice_date TEXT,
    total        INTEGER NOT NULL,
    score        INTEGER NOT NULL DEFAULT 0,
    status       TEXT NOT NULL DEFAULT 'BERSIH'
);

CREATE TABLE IF NOT EXISTS findings (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id TEXT REFERENCES invoices (invoice_id),
    vendor_id  TEXT NOT NULL,
    check_type TEXT NOT NULL,
    weight     INTEGER NOT NULL DEFAULT 0,
    detail     TEXT
);

CREATE INDEX IF NOT EXISTS idx_findings_invoice ON findings (invoice_id);
CREATE INDEX IF NOT EXISTS idx_findings_type ON findings (check_type);
CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices (status);
