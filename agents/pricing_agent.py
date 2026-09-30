"""pricing_agent.py — Pricing Agent.

Kaam: qeemat ke faisle. Sirf tools/pricing.py istemal karta hai —
khud kabhi number nahi banata.

Allowed: READ pricing tables + WRITE pricing_rules, rate_history.
Har rule change audit_log mein darj hota hai.
"""
from agents.base import audit, can_write
import tools.pricing as pricing

AGENT = "pricing"


def quote_for(customer_id, product_id, qty=1):
    """Gahak ke liye rate nikalo (deterministic)."""
    return pricing.quote(customer_id, product_id, qty, by="pricing")


def set_special_rate(customer_id, product_id, rate, scope_detail, by="Azhar"):
    """Azhar ki taraf se special rate lagao. Scope poochna zaroori hai
    (single/temporary/future/permanent) — scope_detail mein likha hoga."""
    if not can_write(AGENT, "pricing_rules"):
        return {"ok": False, "error": "permission nahi"}
    old = pricing.last_rate(customer_id, product_id)
    r = pricing.set_rule(customer_id=customer_id, product_id=product_id,
                         rule_type="fixed_rate", fixed_rate=rate,
                         scope="customer_product", by=by)
    if r["ok"]:
        audit(by, "set_special_rate", "pricing_rules", r["rule_id"],
              old=(old["quoted_rate"] if old else None), new=rate,
              note=scope_detail)
    return r


def set_customer_margin(customer_id, margin_pct, by="Azhar"):
    """Customer ke liye margin % set karo."""
    if not can_write(AGENT, "pricing_rules"):
        return {"ok": False, "error": "permission nahi"}
    r = pricing.set_rule(customer_id=customer_id, rule_type="margin_pct",
                         margin_pct=margin_pct, scope="customer", by=by)
    if r["ok"]:
        audit(by, "set_customer_margin", "pricing_rules", r["rule_id"],
              new=f"{margin_pct}%")
    return r


def set_temporary_rate(customer_id, product_id, rate, ends_at, by="Azhar"):
    """Aarzi rate (expiry ke saath)."""
    if not can_write(AGENT, "pricing_rules"):
        return {"ok": False, "error": "permission nahi"}
    r = pricing.set_rule(customer_id=customer_id, product_id=product_id,
                         rule_type="temporary", fixed_rate=rate,
                         scope="temporary", ends_at=ends_at, by=by)
    if r["ok"]:
        audit(by, "set_temporary_rate", "pricing_rules", r["rule_id"],
              new=f"Rs {rate} until {ends_at}")
    return r


def remove_rule(rule_id, by="Azhar"):
    """Rule hatao (deactivate)."""
    if not can_write(AGENT, "pricing_rules"):
        return {"ok": False, "error": "permission nahi"}
    from tools.db import connect, now_pk
    con = connect()
    try:
        old = con.execute("SELECT * FROM pricing_rules WHERE id=?",
                          (rule_id,)).fetchone()
        if not old:
            return {"ok": False, "error": "rule nahi mila"}
        con.execute("UPDATE pricing_rules SET active=0 WHERE id=?", (rule_id,))
        con.commit()
    finally:
        con.close()
    audit(by, "remove_rule", "pricing_rules", rule_id,
          old=dict(old)["rule_type"], new="inactive")
    return {"ok": True}
