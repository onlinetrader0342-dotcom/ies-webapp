"""base.py — Agent bunyad: permissions, audit, context.

Har agent:
- sirf apne allowed tools chala sakta hai (permission check)
- har WRITE audit log mein darj hota hai (kaun, kab, kya, purani/nayi value)
- context sirf zaroorat ka milta hai (minimum necessary data)
"""
from tools.db import connect, now_pk

# Agent -> allowed tools (READ/WRITE). Sensitive = approval chahiye (Phase 4+).
PERMISSIONS = {
    "inquiry":  {"read": ["customers", "products", "purchase_rates", "stock",
                          "pricing_rules", "rate_history", "business_rules",
                          "suppliers"],
                 "write": []},
    "pricing":  {"read": ["customers", "products", "purchase_rates",
                          "pricing_rules", "rate_history", "business_rules"],
                 "write": ["pricing_rules", "rate_history"]},
    "manager":  {"read": ["*"], "write": []},
    "inventory": {"read": ["products", "stock", "stock_moves", "purchase_rates",
                           "suppliers", "business_rules"],
                  "write": ["stock", "stock_moves", "purchase_rates"]},
    "billing":  {"read": ["customers", "products", "purchase_rates", "stock",
                          "pricing_rules", "rate_history"],
                 "write": ["invoices", "invoice_items", "ledger_entries"]},
    "ledger":   {"read": ["customers", "ledger_entries", "payments"],
                 "write": ["payments", "ledger_entries"]},
    "supplier": {"read": ["products", "suppliers", "purchase_rates", "tasks"],
                 "write": ["tasks"]},
    "staff":    {"read": ["staff", "tasks"], "write": ["tasks"]},
    "rules":    {"read": ["customers", "products", "suppliers", "business_rules",
                          "pricing_rules"],
                 "write": ["business_rules", "pricing_rules"]},
    "reports":  {"read": ["invoices", "invoice_items", "ledger_entries",
                          "stock", "products", "customers"],
                 "write": []},
    "expense":  {"read": ["expenses", "invoices"], "write": ["expenses"]},
    "planning": {"read": ["products", "stock", "suppliers", "purchase_rates", "tasks"],
                 "write": ["tasks"]},
}


def can_read(agent, table):
    p = PERMISSIONS.get(agent, {})
    return "*" in p.get("read", []) or table in p.get("read", [])


def can_write(agent, table):
    p = PERMISSIONS.get(agent, {})
    return "*" in p.get("write", []) or table in p.get("write", [])


def audit(by, action, table, ref_id, old=None, new=None, note=None):
    """Har important change ka record audit_log mein."""
    con = connect()
    try:
        con.execute(
            """INSERT INTO audit_log (at, by_agent, action, tbl, ref_id, old_val, new_val, note)
               VALUES (?,?,?,?,?,?,?,?)""",
            (now_pk(), by, action, table, str(ref_id),
             None if old is None else str(old),
             None if new is None else str(new), note))
        con.commit()
    finally:
        con.close()
