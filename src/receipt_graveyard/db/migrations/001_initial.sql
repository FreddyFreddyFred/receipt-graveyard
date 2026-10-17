-- Initial schema migration. Keep this in sync with ../schema.sql.
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS employees (
    employee_id TEXT PRIMARY KEY NOT NULL CHECK (length(employee_id) > 0),
    name TEXT,
    department TEXT,
    trip_id TEXT,
    city TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS receipts (
    receipt_id TEXT PRIMARY KEY NOT NULL CHECK (length(receipt_id) > 0),
    employee_id TEXT REFERENCES employees(employee_id)
        ON UPDATE CASCADE ON DELETE SET NULL,
    vendor TEXT,
    receipt_date TEXT,
    total TEXT,
    currency TEXT CHECK (currency IS NULL OR length(currency) = 3),
    line_items_json TEXT NOT NULL DEFAULT '[]',
    tax TEXT,
    tip TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS verdicts (
    receipt_id TEXT PRIMARY KEY NOT NULL
        REFERENCES receipts(receipt_id) ON UPDATE CASCADE ON DELETE CASCADE,
    status TEXT NOT NULL
        CHECK (status IN ('Approved', 'Flagged for Review', 'Denied')),
    reasons_json TEXT NOT NULL DEFAULT '[]',
    rule_ids_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_log (
    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL CHECK (length(entity_type) > 0),
    entity_id TEXT NOT NULL CHECK (length(entity_id) > 0),
    receipt_id TEXT REFERENCES receipts(receipt_id)
        ON UPDATE CASCADE ON DELETE SET NULL,
    action TEXT NOT NULL CHECK (length(action) > 0),
    details_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_receipts_employee_date
    ON receipts(employee_id, receipt_date);
CREATE INDEX IF NOT EXISTS idx_verdicts_status
    ON verdicts(status);
CREATE INDEX IF NOT EXISTS idx_audit_log_receipt_created
    ON audit_log(receipt_id, created_at);
