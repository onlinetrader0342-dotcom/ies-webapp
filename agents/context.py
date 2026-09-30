"""context.py — Context Engineering: Right Agent + Right Tool + Right Context + Right Time.

Har request par POORA database nahi milta. Sirf woh layers jo is kaam ke liye zaroori hain.
"""
from tools.db import connect
from agents.base import can_read
import tools.pricing as pricing


def customer_by_phone(phone):
    con = connect()
    try:
        return con.execute("SELECT * FROM customers WHERE phone=?", (phone,)).fetchone()
    finally:
        con.close()


def customer_by_name(name):
    con = connect()
    try:
        return con.execute("SELECT * FROM customers WHERE lower(name)=lower(?)",
                           (name,)).fetchone()
    finally:
        con.close()


def active_business_rules(scope=None, ref=None):
    """Laagoo business rules (global + scope ke)."""
    con = connect()
    try:
        if scope:
            rows = con.execute(
                """SELECT * FROM business_rules WHERE active=1
                   AND (scope='global' OR (scope=? AND (scope_ref IS NULL OR scope_ref=?)))""",
                (scope, ref)).fetchall()
        else:
            rows = con.execute(
                "SELECT * FROM business_rules WHERE active=1 AND scope='global'").fetchall()
        return [dict(r) for r in rows]
    finally:
        con.close()


def gather_inquiry_context(agent, customer_id, product_id):
    """Customer Inquiry ke liye zaroori context — sirf yehi layers."""
    assert can_read(agent, "products")
    ctx = {}
    prod = pricing.get_product(product_id)
    ctx["product"] = dict(prod) if prod else None
    ctx["purchase_rate"] = pricing.purchase_rate(product_id)
    con = connect()
    try:
        s = con.execute("SELECT quantity FROM stock WHERE product_id=?",
                        (product_id,)).fetchone()
        ctx["stock"] = s["quantity"] if s else 0
        if customer_id:
            cust = con.execute("SELECT * FROM customers WHERE id=?",
                               (customer_id,)).fetchone()
            ctx["customer"] = dict(cust) if cust else None
            lr = pricing.last_rate(customer_id, product_id)
            ctx["last_rate"] = lr
            # outstanding
            bal = con.execute(
                """SELECT COALESCE(SUM(CASE WHEN kind='sale' THEN amount
                       WHEN kind='payment' THEN -amount
                       WHEN kind='adjustment' THEN amount ELSE 0 END),0) AS bal
                   FROM ledger_entries WHERE customer_id=?""",
                (customer_id,)).fetchone()
            ctx["outstanding"] = bal["bal"]
        else:
            ctx["customer"] = None
            ctx["last_rate"] = None
            ctx["outstanding"] = 0
    finally:
        con.close()
    ctx["rules"] = active_business_rules("product", str(product_id))
    return ctx
