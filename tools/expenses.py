"""expenses.py — Dukaan ke kharchay. Asal munafa = gross profit - kharchay."""
from tools.db import connect, now_pk
from agents.base import audit
from tools import billing

CATEGORIES = ["kiraya", "bijli", "tankhwah", "transport", "chaay_pani",
              "maintenance", "tax", "doosra"]


def add_expense(category, amount, note=None, by="Azhar"):
    if amount <= 0:
        return {"ok": False, "error": "raqam 0 se zyada honi chahiye"}
    cat = category.lower().replace(" ", "_")
    if cat not in CATEGORIES:
        cat = "doosra"
    con = connect()
    try:
        cur = con.execute(
            "INSERT INTO expenses (category, amount, at, note, by) VALUES (?,?,?,?,?)",
            (cat, amount, now_pk(), note, by))
        con.commit()
        eid = cur.lastrowid
    finally:
        con.close()
    audit(by, "add_expense", "expenses", eid, new=f"{cat} Rs {amount}")
    return {"ok": True, "id": eid}


def total_expenses(days=30):
    con = connect()
    try:
        r = con.execute(
            "SELECT COALESCE(SUM(amount),0) t FROM expenses WHERE at >= datetime('now', ?)",
            (f"-{days} days",)).fetchone()
        return r["t"]
    finally:
        con.close()


def by_category(days=30):
    con = connect()
    try:
        return [dict(r) for r in con.execute(
            """SELECT category, SUM(amount) t, COUNT(*) n FROM expenses
               WHERE at >= datetime('now', ?) GROUP BY category ORDER BY t DESC""",
            (f"-{days} days",))]
    finally:
        con.close()


def gross_profit(days=30):
    con = connect()
    try:
        r = con.execute(
            "SELECT COALESCE(SUM(profit),0) p FROM invoices WHERE at >= datetime('now', ?)",
            (f"-{days} days",)).fetchone()
        return r["p"]
    finally:
        con.close()


def net_profit(days=30):
    """Asal munafa = gross profit - kharchay."""
    return gross_profit(days) - total_expenses(days)


def summary(days=30):
    g, e = gross_profit(days), total_expenses(days)
    lines = [f"Pichle {days} din: gross profit Rs {g}, kharchay Rs {e}, "
             f"ASAL MUNAFA Rs {g - e}."]
    for c in by_category(days)[:5]:
        lines.append(f"  - {c['category']}: Rs {c['t']}")
    return "\n".join(lines)
