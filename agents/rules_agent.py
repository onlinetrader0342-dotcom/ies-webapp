"""rules_agent.py — Business Rules Agent.

Azhar Roman Urdu mein usool bolega, agent usay structured rule banayega:
  scope: temporary | customer | product | customer_product | supplier | agent | global

Qeemat wale usool (margin/discount/rate) → pricing_agent ko bhejta hai.
Baqi usool → business_rules table mein.

Misal:
  "Atif ko hamesha 10% riayat do"      → pricing rule (customer margin)
  "Jumme ko dukaan 2 baje band"        → business rule (global)
  "Is hafte Shahid se khareedna"       → business rule (supplier, temporary)
"""
import re
from tools.db import connect, now_pk
from agents.base import audit, can_write
from agents import pricing_agent
from agents.context import customer_by_name
import tools.pricing as pricing

AGENT = "rules"

TEMP_WORDS = ["aaj", "kal", "is hafte", "is mahine", "temporary", "aarzi",
              "kuch din", "filhal"]
PERM_WORDS = ["hamesha", "mustaqil", "permanent", "hamesha ke liye"]


def detect_scope(text):
    """(scope, customer_id, product_id, supplier_id)"""
    t = text.lower()
    cid, pid, sid = None, None, None

    # customer?
    con = connect()
    try:
        for c in con.execute("SELECT id, name FROM customers").fetchall():
            if c["name"].lower() in t:
                cid = c["id"]
                break
        # supplier?
        for s in con.execute("SELECT id, name FROM suppliers").fetchall():
            if s["name"].lower() in t:
                sid = s["id"]
                break
    finally:
        con.close()

    # product?
    cands = pricing.find_product(t)
    if cands and cands[0]["_score"] >= 2:
        pid = cands[0]["id"]

    is_temp = any(w in t for w in TEMP_WORDS)
    if is_temp:
        return ("temporary", cid, pid, sid)
    if cid and pid:
        return ("customer_product", cid, pid, sid)
    if cid:
        return ("customer", cid, pid, sid)
    if pid:
        return ("product", cid, pid, sid)
    if sid:
        return ("supplier", cid, pid, sid)
    return ("global", cid, pid, sid)


def is_pricing_rule(text):
    t = text.lower()
    return bool(re.search(r"(\d+)\s*%\s*(riayat|discount|margin|chhoot|kam)", t) or
                re.search(r"(rate|qeemat)\s*(fix|muqarrar|set)", t) or
                re.search(r"(special|khaas)\s*rate", t))


def add_rule(text, by="Azhar"):
    """Natural language → structured rule. Returns wazahat."""
    if not can_write(AGENT, "business_rules"):
        return "Permission nahi."

    # qeemat wala usool → pricing agent
    if is_pricing_rule(text):
        return _pricing_rule_from_text(text, by)

    scope, cid, pid, sid = detect_scope(text)
    scope_ref = None
    if scope == "customer":
        scope_ref = str(cid)
    elif scope == "product":
        scope_ref = str(pid)
    elif scope == "customer_product":
        scope_ref = f"{cid}:{pid}"
    elif scope == "supplier":
        scope_ref = str(sid)

    con = connect()
    try:
        cur = con.execute(
            """INSERT INTO business_rules (text, scope, scope_ref, active, created_by, created_at)
               VALUES (?,?,?,?,?,?)""",
            (text.strip(), scope, scope_ref, 1, by, now_pk()))
        con.commit()
        rid = cur.lastrowid
    finally:
        con.close()
    audit(by, "add_rule", "business_rules", rid, new=f"[{scope}] {text[:60]}")
    scope_ur = {"temporary": "aarzi", "customer": "customer", "product": "product",
                "customer_product": "customer+product", "supplier": "supplier",
                "agent": "agent", "global": "sab ke liye"}[scope]
    return f"Usool darj ho gaya (#{rid}) — scope: {scope_ur}."


def _pricing_rule_from_text(text, by):
    """'Atif ko 10% riayat' → pricing rule."""
    t = text.lower()
    m = re.search(r"(\d+)\s*%", t)
    if not m:
        return "Kitne % riayat? Samajh nahi aaya."
    pct = float(m.group(1))
    # riayat = default 20% margin se kami. "10% riayat" → 10% margin.
    margin = max(0.0, 20.0 - pct)
    scope, cid, pid, sid = detect_scope(text)
    if scope == "customer_product":
        r = pricing.set_rule(customer_id=cid, product_id=pid,
                             rule_type="margin_pct", margin_pct=margin,
                             scope="customer_product", by=by)
    elif scope in ("customer", "temporary") and cid:
        r = pricing_agent.set_customer_margin(cid, margin, by=by)
    else:
        return "Kis customer ko riayat? Naam batayein."
    if r["ok"]:
        audit(by, "add_rule_pricing", "pricing_rules", r["rule_id"],
              new=f"{pct}% riayat → margin {margin}%")
        return f"Riayat lag gayi: {pct}% (ab margin {margin}%)."
    return f"Masla: {r.get('error')}"


def list_rules(scope=None):
    con = connect()
    try:
        if scope:
            rows = con.execute(
                "SELECT * FROM business_rules WHERE active=1 AND scope=? ORDER BY id DESC",
                (scope,)).fetchall()
        else:
            rows = con.execute(
                "SELECT * FROM business_rules WHERE active=1 ORDER BY id DESC").fetchall()
        if not rows:
            return "Koi usool darj nahi."
        return "\n".join(f"#{r['id']} [{r['scope']}] {r['text']}" for r in rows)
    finally:
        con.close()


def remove_rule(rule_id, by="Azhar"):
    if not can_write(AGENT, "business_rules"):
        return "Permission nahi."
    con = connect()
    try:
        r = con.execute("SELECT * FROM business_rules WHERE id=?", (rule_id,)).fetchone()
        if not r:
            return "Usool nahi mila."
        con.execute("UPDATE business_rules SET active=0 WHERE id=?", (rule_id,))
        con.commit()
    finally:
        con.close()
    audit(by, "remove_rule", "business_rules", rule_id, old=r["text"][:50])
    return f"Usool #{rule_id} hata diya."


def handle(text, by="Azhar"):
    t = text.lower()
    if t.startswith("usool") or t.startswith("rule"):
        rest = re.sub(r"^(usool|rule)\s+", "", t, count=1)
        if rest.startswith("list") or rest.startswith("dekho"):
            return list_rules()
        m = re.match(r"(hatao|remove|khatam)\s+(\d+)", rest)
        if m:
            return remove_rule(int(m.group(2)), by)
        m = re.match(r"(banao|add)\s+(.+)", rest)
        if m:
            return add_rule(m.group(2), by)
        # seedha usool ka text
        if rest:
            return add_rule(rest, by)
    return "Usool: 'usool banao <tumhara usool>', 'usool list', 'usool hatao <id>'."
