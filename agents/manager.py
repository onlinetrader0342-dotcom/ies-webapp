"""manager.py — Central Manager Agent.

Kaam: har aane wale paigham ko sahi agent tak pahunchana,
sahi context ke saath, sahi waqt par.

Flow: paigham → customer pehchano → niyat → agent chunno →
      agent chalao → jawab wapas.

Abhi routing keywords se hai (deterministic). Baad mein LLM
hook lagega — interface wahi rahega.
"""
import re
from agents.context import customer_by_phone
from agents import (inquiry_agent, pricing_agent, inventory_agent,
                    billing_agent, ledger_agent, supplier_agent,
                    staff_agent, reports_agent, rules_agent, expense_agent,
                    planning_agent)

AGENT = "manager"

# Manager ke apne commands (Azhar ke liye)
ADMIN_PATTERNS = [
    (r"special rate (\d+)\s+(.+?)\s+(\d+)", "special"),   # special rate <cust_id> <prod> <rate>
    (r"margin (\d+)\s+(\d+)", "margin"),                  # margin <cust_id> <pct>
]


def identify_customer(sender):
    """sender = phone ya naam. Returns customer_id ya None."""
    if not sender:
        return None
    c = customer_by_phone(sender)
    if c:
        return c["id"]
    return None


def route(text):
    """Kaunsa agent? Returns (agent_name, intent)."""
    t = text.lower()
    # Admin commands → pricing agent (Azhar)
    for pat, _ in ADMIN_PATTERNS:
        if re.search(pat, t):
            return ("pricing", "admin")
    if re.match(r"\s*bill\s+\d+", t):
        return ("billing", "bill")
    if re.search(r"\b(payment|khata)\b", t):
        return ("ledger", "ledger")
    if (re.search(r"\bstock in\b", t) or "low stock" in t or "kam stock" in t
            or re.search(r"\bstock\b.*\?", t) or re.search(r"\bstock\b", t) and "rate" not in t):
        return ("inventory", "inventory")
    if re.search(r"\btask\b", t):
        return ("staff", "staff")
    if t.startswith("usool") or t.startswith("rule"):
        return ("rules", "rules")
    if "kharcha" in t or "kharchay" in t or "expense" in t:
        return ("expense", "expense")
    if re.search(r"\border\b", t) and re.search(r"(list|banao|suggest|planning|mangwa)", t):
        return ("planning", "planning")
    if re.search(r"\b(report|profit|munafa|hisab kitab)\b", t):
        return ("reports", "report")
    if "supplier" in t or "rate request" in t:
        return ("supplier", "supplier")
    intent = inquiry_agent.classify(text)
    if intent in ("product", "order", "discount", "balance", "greeting", "thanks"):
        return ("inquiry", intent)
    return ("inquiry", "unknown")


def handle_message(sender, text):
    """Ek paigham ka mukammal jawab. Returns Roman Urdu string."""
    customer_id = identify_customer(sender)
    agent_name, intent = route(text)

    if agent_name == "pricing" and intent == "admin":
        return _handle_admin(text)

    # product nikalne ki koshish (agar product wali baat hai)
    product_id = None
    if intent in ("product", "order", "discount"):
        import tools.pricing as pricing
        cands = pricing.find_product(text)
        # behtareen match wazeh ho to wahi lo (score >= 2 ya waahid umeedwar)
        if cands and (cands[0]["_score"] >= 2 or len(cands) == 1):
            product_id = cands[0]["id"]

    cid = customer_id or 0  # 0 = unknown walk-in
    if agent_name == "billing":
        return billing_agent.handle(cid, text)
    if agent_name == "ledger":
        return ledger_agent.handle(cid, text)
    if agent_name == "inventory":
        return inventory_agent.handle(text)
    if agent_name == "staff":
        return staff_agent.handle(text)
    if agent_name == "reports":
        return reports_agent.handle(text)
    if agent_name == "rules":
        return rules_agent.handle(text)
    if agent_name == "expense":
        return expense_agent.handle(text)
    if agent_name == "planning":
        return planning_agent.handle(text)
    if agent_name == "supplier":
        return supplier_agent.rate_request_draft(
            _extract_product_id(text) or 0)
    return inquiry_agent.handle(cid if cid else None, product_id, text)


def _extract_product_id(text):
    import tools.pricing as pricing
    cands = pricing.find_product(text)
    if cands and (cands[0]["_score"] >= 2 or len(cands) == 1):
        return cands[0]["id"]
    return None


def _handle_admin(text):
    """Azhar ke commands: 'special rate <cust> <product_id> <rate>' etc."""
    t = text.lower()
    m = re.search(r"special rate (\d+)\s+(\d+)\s+(\d+)", t)
    if m:
        cid, pid, rate = int(m.group(1)), int(m.group(2)), int(m.group(3))
        r = pricing_agent.set_special_rate(cid, pid, rate,
                                           "admin command se lagaya")
        if r["ok"]:
            return f"Special rate lag gaya: customer {cid}, product {pid} = Rs {rate}."
        return f"Masla: {r.get('error')}"
    m = re.search(r"margin (\d+)\s+(\d+)", t)
    if m:
        cid, pct = int(m.group(1)), int(m.group(2))
        r = pricing_agent.set_customer_margin(cid, pct)
        if r["ok"]:
            return f"Margin set: customer {cid} par {pct}%."
        return f"Masla: {r.get('error')}"
    return "Admin command samajh nahi aaya."


if __name__ == "__main__":
    import sys
    sender = sys.argv[1] if len(sys.argv) > 1 else ""
    text = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
    print(handle_message(sender, text))
