#!/usr/bin/env python3
"""Seed db/shop.db from price-list markdown files. Idempotent, stdlib only."""
import re
import sqlite3
from pathlib import Path
from datetime import datetime, timezone, timedelta

DB_DIR = Path(__file__).parent
DB_PATH = DB_DIR / "shop.db"
SCHEMA_PATH = DB_DIR / "schema.sql"

OSTRIC_MD = Path("/home/hatch/.openclaw/workspace/products-ostric.md")
LSCABLE_MD = Path("/home/hatch/.openclaw/workspace/products-lscable.md")
SUPPLIERS_MD = Path("/home/hatch/workspace/workers/salesman/suppliers.md")

# Asia/Karachi is UTC+5, no DST
KARACHI = timezone(timedelta(hours=5))
OPENING_AT = "2026-09-20 00:00:00"


def now_karachi() -> str:
    return datetime.now(KARACHI).strftime("%Y-%m-%d %H:%M:%S")


def parse_price(raw: str) -> int:
    raw = raw.strip().replace(",", "").strip()
    # Range like "800-850" or "800–850" (en-dash) -> take first number
    for sep in ("–", "—", "-"):
        if sep in raw:
            raw = raw.split(sep)[0].strip()
            break
    # Remove any non-digit leftovers
    m = re.search(r"\d+", raw)
    if not m:
        raise ValueError(f"Cannot parse price: {raw!r}")
    return int(m.group(0))


def parse_products_file(path: Path, brand: str) -> list[dict]:
    products = []
    is_special_section = False
    text = path.read_text(encoding="utf-8")
    for line in text.splitlines():
        if "Special Discounted Items" in line:
            is_special_section = True
            continue
        line = line.strip()
        if not line.startswith("|"):
            continue
        # skip header and separator rows
        if "Product" in line and "Detail" in line and "Price" in line:
            continue
        if re.match(r"^\|\s*-+", line):
            continue
        parts = [p.strip() for p in line.split("|")]
        # split gives ['', col1, col2, col3, ''] for 3-col table
        # filter empties at ends
        if parts and parts[0] == "":
            parts = parts[1:]
        if parts and parts[-1] == "":
            parts = parts[:-1]
        if len(parts) < 3:
            continue
        name, detail, price_raw = parts[0], parts[1], parts[2]
        if not name or not price_raw:
            continue
        # skip rows where price is not numeric-ish
        if not re.search(r"\d", price_raw):
            continue
        try:
            price = parse_price(price_raw)
        except ValueError:
            continue
        products.append({
            "name": name,
            "detail": detail,
            "brand": brand,
            "price": price,
            "is_special": 1 if is_special_section else 0,
        })
    return products


def parse_suppliers(path: Path) -> list[dict]:
    suppliers = []
    text = path.read_text(encoding="utf-8")
    current = None
    for line in text.splitlines():
        line = line.strip()
        m = re.match(r"^##\s+(.+)", line)
        if m:
            if current:
                suppliers.append(current)
            current = {"name": m.group(1).strip(), "whatsapp": "", "deals": "", "keywords": ""}
            continue
        if current is None:
            continue
        low = line.lower()
        if low.startswith("- whatsapp:"):
            current["whatsapp"] = line.split(":", 1)[1].strip()
        elif low.startswith("- deals:"):
            current["deals"] = line.split(":", 1)[1].strip()
        elif low.startswith("- keywords:"):
            current["keywords"] = line.split(":", 1)[1].strip()
    if current:
        suppliers.append(current)
    return suppliers


def main():
    DB_DIR.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(DB_PATH))
    con.execute("PRAGMA foreign_keys = ON")

    # Apply schema (idempotent via IF NOT EXISTS)
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    con.executescript(schema_sql)

    # --- Products ---
    all_products = []
    if OSTRIC_MD.exists():
        all_products.extend(parse_products_file(OSTRIC_MD, "Ostric"))
    if LSCABLE_MD.exists():
        all_products.extend(parse_products_file(LSCABLE_MD, "LS Cable"))

    now = now_karachi()

    for p in all_products:
        con.execute(
            "INSERT OR IGNORE INTO products (name, detail, brand, is_special) VALUES (?, ?, ?, ?)",
            (p["name"], p["detail"], p["brand"], p["is_special"]),
        )
        row = con.execute(
            "SELECT id FROM products WHERE name=? AND detail=? AND brand=?",
            (p["name"], p["detail"], p["brand"]),
        ).fetchone()
        if row is None:
            continue
        pid = row[0]
        # purchase_rates opening
        exists = con.execute(
            "SELECT 1 FROM purchase_rates WHERE product_id=? AND note='opening' LIMIT 1", (pid,)
        ).fetchone()
        if not exists:
            con.execute(
                "INSERT INTO purchase_rates (product_id, rate, supplier_id, at, note) VALUES (?, ?, NULL, ?, 'opening')",
                (pid, p["price"], OPENING_AT),
            )
        # stock
        con.execute(
            "INSERT OR IGNORE INTO stock (product_id, quantity, updated_at) VALUES (?, 0, ?)",
            (pid, now),
        )

    # --- Suppliers ---
    if SUPPLIERS_MD.exists():
        for s in parse_suppliers(SUPPLIERS_MD):
            con.execute(
                "INSERT OR IGNORE INTO suppliers (name, whatsapp, deals, keywords) VALUES (?, ?, ?, ?)",
                (s["name"], s["whatsapp"], s["deals"], s["keywords"]),
            )

    # --- Customer Atif ---
    con.execute(
        "INSERT OR IGNORE INTO customers (name, phone, address, notes, created_at) VALUES (?, NULL, NULL, ?, ?)",
        ("Atif", "opening udhaar Rs 2500 (2026-09-20)", OPENING_AT),
    )
    atif = con.execute("SELECT id FROM customers WHERE name='Atif'").fetchone()
    if atif:
        atif_id = atif[0]
        exists = con.execute(
            "SELECT 1 FROM ledger_entries WHERE customer_id=? AND note='opening udhaar' AND kind='sale' AND amount=2500 LIMIT 1",
            (atif_id,),
        ).fetchone()
        if not exists:
            con.execute(
                "INSERT INTO ledger_entries (customer_id, kind, amount, ref, at, note) VALUES (?, 'sale', 2500, NULL, ?, 'opening udhaar')",
                (atif_id, OPENING_AT),
            )

    # --- Staff ---
    con.execute(
        "INSERT OR IGNORE INTO staff (name, phone, role) VALUES ('Azhar', NULL, 'owner')"
    )

    con.commit()

    # --- Verify counts ---
    counts = {}
    for tbl in ["products", "purchase_rates", "stock", "suppliers", "customers", "ledger_entries", "staff"]:
        counts[tbl] = con.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]

    # Detailed breakdown
    ostric_count = con.execute("SELECT COUNT(*) FROM products WHERE brand='Ostric'").fetchone()[0]
    lscable_count = con.execute("SELECT COUNT(*) FROM products WHERE brand='LS Cable'").fetchone()[0]
    special_count = con.execute("SELECT COUNT(*) FROM products WHERE is_special=1").fetchone()[0]

    print(f"DB: {DB_PATH}")
    print(f"products: {counts['products']} (Ostric={ostric_count}, LS Cable={lscable_count}, special={special_count})")
    print(f"purchase_rates: {counts['purchase_rates']}")
    print(f"stock: {counts['stock']}")
    print(f"suppliers: {counts['suppliers']}")
    print(f"customers: {counts['customers']}")
    print(f"ledger_entries: {counts['ledger_entries']}")
    print(f"staff: {counts['staff']}")
    print("Seed complete (idempotent — dobara chalane par duplicate nahi bane ga).")

    con.close()


if __name__ == "__main__":
    main()
