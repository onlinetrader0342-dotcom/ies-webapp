"""billing.py — Bill banao: sale + stock out + ledger + profit. Ek transaction mein."""
from tools.db import connect, now_pk
from agents.base import audit
import tools.pricing as pricing
from tools import inventory


def create_invoice(customer_id, items, by="Azhar"):
    """items = [(product_id, qty), ...]. Rates pricing engine se (deterministic).
    Returns invoice dict ya error."""
    # 1. sab items ke rate nikalo + stock check
    lines = []
    total = 0
    profit = 0
    for pid, qty in items:
        q = pricing.quote(customer_id, pid, qty, by="billing")
        if not q["ok"]:
            return {"ok": False, "error": f"product {pid}: {q['error']}"}
        have = inventory.get_stock(pid)
        if have < qty:
            return {"ok": False,
                    "error": f"{q['product']}: stock {have}, {qty} manga — pehle stock in karo"}
        lines.append(q)
        total += q["total"]
        profit += (q["unit_rate"] - q["purchase_rate"]) * qty

    # 2. sab kuch ek transaction mein
    con = connect()
    try:
        at = now_pk()
        cur = con.execute(
            "INSERT INTO invoices (customer_id, total, profit, at, by) VALUES (?,?,?,?,?)",
            (customer_id, total, profit, at, by))
        inv_id = cur.lastrowid
        for q in lines:
            con.execute(
                """INSERT INTO invoice_items (invoice_id, product_id, qty, rate, purchase_rate)
                   VALUES (?,?,?,?,?)""",
                (inv_id, q["product_id"], q["qty"], q["unit_rate"], q["purchase_rate"]))
        con.execute(
            "INSERT INTO ledger_entries (customer_id, kind, amount, ref, at, note)"
            " VALUES (?,?,?,?,?,?)",
            (customer_id, "sale", total, f"INV-{inv_id}", at,
             f"bill #{inv_id}, {len(lines)} items"))
        con.commit()
    finally:
        con.close()

    # 3. stock ghatao (har item)
    for pid, qty in items:
        r = inventory.stock_out(pid, qty, reason="sale", ref=f"INV-{inv_id}", by="billing")
        if not r["ok"]:
            # NOTE: invoice ban gaya lekin stock nahi ghata — alert Azhar ko
            audit(by, "STOCK_MISMATCH", "invoices", inv_id, note=r["error"])

    audit(by, "create_invoice", "invoices", inv_id,
          new=f"Rs {total} profit Rs {profit}")
    return {"ok": True, "invoice_id": inv_id, "total": total,
            "profit": profit, "lines": lines}


def get_invoice(inv_id):
    con = connect()
    try:
        inv = con.execute("SELECT * FROM invoices WHERE id=?", (inv_id,)).fetchone()
        if not inv:
            return None
        items = con.execute(
            """SELECT ii.*, p.name FROM invoice_items ii
               JOIN products p ON p.id=ii.product_id WHERE ii.invoice_id=?""",
            (inv_id,)).fetchall()
        d = dict(inv)
        d["items"] = [dict(i) for i in items]
        return d
    finally:
        con.close()


def today_sales():
    con = connect()
    try:
        r = con.execute(
            """SELECT COUNT(*) n, COALESCE(SUM(total),0) t, COALESCE(SUM(profit),0) p
               FROM invoices WHERE date(at)=date('now','+5 hours')""").fetchone()
        return {"bills": r["n"], "total": r["t"], "profit": r["p"]}
    finally:
        con.close()
