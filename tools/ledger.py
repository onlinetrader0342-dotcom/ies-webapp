"""ledger.py — Customer khata: sale, payment, adjustment, outstanding."""
from tools.db import connect, now_pk
from agents.base import audit


def outstanding(customer_id):
    con = connect()
    try:
        r = con.execute(
            """SELECT COALESCE(SUM(CASE WHEN kind='sale' THEN amount
                   WHEN kind='payment' THEN -amount
                   WHEN kind='adjustment' THEN amount ELSE 0 END),0) AS bal
               FROM ledger_entries WHERE customer_id=?""",
            (customer_id,)).fetchone()
        return r["bal"]
    finally:
        con.close()


def record_payment(customer_id, amount, note=None, by="Azhar"):
    if amount <= 0:
        return {"ok": False, "error": "raqam 0 se zyada honi chahiye"}
    con = connect()
    try:
        at = now_pk()
        cur = con.execute(
            "INSERT INTO payments (customer_id, amount, at, note) VALUES (?,?,?,?)",
            (customer_id, amount, at, note))
        con.execute(
            "INSERT INTO ledger_entries (customer_id, kind, amount, ref, at, note)"
            " VALUES (?,?,?,?,?,?)",
            (customer_id, "payment", amount, f"PAY-{cur.lastrowid}", at, note))
        con.commit()
    finally:
        con.close()
    audit(by, "record_payment", "payments", cur.lastrowid,
          new=f"Rs {amount} customer {customer_id}")
    return {"ok": True, "new_outstanding": outstanding(customer_id)}


def adjustment(customer_id, amount, note, by="Azhar"):
    """+amount = customer par charhao, -amount = maaf/discount."""
    con = connect()
    try:
        at = now_pk()
        con.execute(
            "INSERT INTO ledger_entries (customer_id, kind, amount, ref, at, note)"
            " VALUES (?,?,?,?,?,?)",
            (customer_id, "adjustment", amount, None, at, note))
        con.commit()
    finally:
        con.close()
    audit(by, "adjustment", "ledger_entries", customer_id,
          new=f"Rs {amount} ({note})")
    return {"ok": True, "new_outstanding": outstanding(customer_id)}


def history(customer_id, limit=20):
    con = connect()
    try:
        return [dict(r) for r in con.execute(
            """SELECT kind, amount, ref, at, note FROM ledger_entries
               WHERE customer_id=? ORDER BY at DESC, id DESC LIMIT ?""",
            (customer_id, limit))]
    finally:
        con.close()


def all_outstanding():
    """Sab customers jinka baqaya > 0."""
    con = connect()
    try:
        return [dict(r) for r in con.execute(
            """SELECT c.id, c.name, c.phone,
               SUM(CASE WHEN l.kind='sale' THEN l.amount
                        WHEN l.kind='payment' THEN -l.amount
                        WHEN l.kind='adjustment' THEN l.amount ELSE 0 END) AS bal
               FROM customers c JOIN ledger_entries l ON l.customer_id=c.id
               GROUP BY c.id HAVING bal > 0 ORDER BY bal DESC""")]
    finally:
        con.close()
