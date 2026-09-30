"""inventory.py — Stock ka hisab. Har in/out yahan se."""
from tools.db import connect, now_pk
from agents.base import audit


def get_stock(product_id):
    con = connect()
    try:
        r = con.execute("SELECT quantity FROM stock WHERE product_id=?",
                        (product_id,)).fetchone()
        return r["quantity"] if r else 0
    finally:
        con.close()


def stock_in(product_id, qty, purchase_rate=None, supplier_id=None,
             note=None, by="Azhar"):
    """Maal aaya: stock barhao + purchase rate history mein nayi row."""
    if qty <= 0:
        return {"ok": False, "error": "qty 0 se zyada honi chahiye"}
    con = connect()
    try:
        at = now_pk()
        con.execute(
            "INSERT INTO stock (product_id, quantity, updated_at) VALUES (?,?,?)"
            " ON CONFLICT(product_id) DO UPDATE SET quantity=quantity+?, updated_at=?",
            (product_id, qty, at, qty, at))
        con.execute(
            "INSERT INTO stock_moves (product_id, qty_change, reason, ref, at)"
            " VALUES (?,?,?,?,?)",
            (product_id, qty, "purchase", note, at))
        if purchase_rate:
            con.execute(
                "INSERT INTO purchase_rates (product_id, rate, supplier_id, at, note)"
                " VALUES (?,?,?,?,?)",
                (product_id, purchase_rate, supplier_id, at, note))
        con.commit()
    finally:
        con.close()
    audit(by, "stock_in", "stock", product_id, new=f"+{qty}")
    return {"ok": True, "new_stock": get_stock(product_id)}


def stock_out(product_id, qty, reason="sale", ref=None, by="system"):
    """Maal gaya: stock ghatao. Kami ho to mana karo."""
    if qty <= 0:
        return {"ok": False, "error": "qty 0 se zyada honi chahiye"}
    have = get_stock(product_id)
    if have < qty:
        return {"ok": False, "error": f"stock kam hai ({have} available, {qty} manga)"}
    con = connect()
    try:
        at = now_pk()
        con.execute(
            "UPDATE stock SET quantity=quantity-?, updated_at=? WHERE product_id=?",
            (qty, at, product_id))
        con.execute(
            "INSERT INTO stock_moves (product_id, qty_change, reason, ref, at)"
            " VALUES (?,?,?,?,?)",
            (product_id, -qty, reason, ref, at))
        con.commit()
    finally:
        con.close()
    audit(by, "stock_out", "stock", product_id, old=have, new=have - qty,
          note=f"{reason} {ref or ''}")
    return {"ok": True, "new_stock": have - qty}


def low_stock(threshold=10):
    con = connect()
    try:
        return [dict(r) for r in con.execute(
            """SELECT p.id, p.name, p.detail, s.quantity FROM stock s
               JOIN products p ON p.id=s.product_id
               WHERE s.quantity <= ? ORDER BY s.quantity""", (threshold,))]
    finally:
        con.close()


def zero_stock():
    return low_stock(0)


def stock_report():
    con = connect()
    try:
        return [dict(r) for r in con.execute(
            """SELECT p.id, p.name, p.detail, p.brand, s.quantity FROM stock s
               JOIN products p ON p.id=s.product_id ORDER BY p.brand, p.name""")]
    finally:
        con.close()
