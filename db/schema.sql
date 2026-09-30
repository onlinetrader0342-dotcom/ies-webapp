-- Electric BMS — SQLite schema
-- Phase 1: database only. Money = INTEGER (Rs), timestamps = TEXT 'YYYY-MM-DD HH:MM:SS' (Asia/Karachi).
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS customers (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL UNIQUE,
    phone      TEXT,
    address    TEXT,
    notes      TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS products (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL,
    detail     TEXT NOT NULL,
    brand      TEXT NOT NULL,
    category   TEXT,
    is_special INTEGER NOT NULL DEFAULT 0,
    UNIQUE(name, detail, brand)
);

CREATE TABLE IF NOT EXISTS suppliers (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    name     TEXT NOT NULL UNIQUE,
    whatsapp TEXT NOT NULL,
    deals    TEXT,
    keywords TEXT
);

CREATE TABLE IF NOT EXISTS purchase_rates (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id  INTEGER NOT NULL REFERENCES products(id),
    rate        INTEGER NOT NULL,
    supplier_id INTEGER REFERENCES suppliers(id),
    at          TEXT NOT NULL,
    note        TEXT
);

CREATE TABLE IF NOT EXISTS stock (
    product_id INTEGER PRIMARY KEY REFERENCES products(id),
    quantity   INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS stock_moves (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL REFERENCES products(id),
    qty_change INTEGER NOT NULL,
    reason     TEXT NOT NULL,
    ref        TEXT,
    at         TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS pricing_rules (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER REFERENCES customers(id),
    product_id  INTEGER REFERENCES products(id),
    rule_type   TEXT NOT NULL CHECK(rule_type IN ('margin_pct','fixed_rate','temporary')),
    margin_pct  REAL,
    fixed_rate  INTEGER,
    scope       TEXT NOT NULL,
    starts_at   TEXT NOT NULL,
    ends_at     TEXT,
    active      INTEGER NOT NULL DEFAULT 1,
    created_by  TEXT NOT NULL,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS invoices (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    total       INTEGER NOT NULL,
    profit      INTEGER NOT NULL,
    at          TEXT NOT NULL,
    by          TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS invoice_items (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id    INTEGER NOT NULL REFERENCES invoices(id),
    product_id    INTEGER NOT NULL REFERENCES products(id),
    qty           INTEGER NOT NULL,
    rate          INTEGER NOT NULL,
    purchase_rate INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS payments (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    amount      INTEGER NOT NULL,
    at          TEXT NOT NULL,
    note        TEXT
);

CREATE TABLE IF NOT EXISTS ledger_entries (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    kind        TEXT NOT NULL CHECK(kind IN ('sale','payment','adjustment')),
    amount      INTEGER NOT NULL,
    ref         TEXT,
    at          TEXT NOT NULL,
    note        TEXT
);

CREATE TABLE IF NOT EXISTS staff (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    name  TEXT NOT NULL UNIQUE,
    phone TEXT,
    role  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tasks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT NOT NULL,
    assigned_to INTEGER REFERENCES staff(id),
    status      TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','assigned','in_progress','collected','received','completed')),
    detail      TEXT,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS business_rules (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    text       TEXT NOT NULL,
    scope      TEXT NOT NULL CHECK(scope IN ('temporary','customer','product','customer_product','supplier','agent','global')),
    scope_ref  TEXT,
    active     INTEGER NOT NULL DEFAULT 1,
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS rate_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    product_id  INTEGER NOT NULL REFERENCES products(id),
    quoted_rate INTEGER NOT NULL,
    sale_rate   INTEGER,
    discount    INTEGER,
    at          TEXT NOT NULL,
    by          TEXT NOT NULL
);
