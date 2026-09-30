"""inquiry_agent.py — Customer Inquiry Agent.

Kaam: customer ka sawal samajh kar relevant context jama karna aur
Roman Urdu jawab banana (templates se — deterministic, model nahi).

Allowed: sirf READ.
"""
import re
from agents.context import gather_inquiry_context
import tools.pricing as pricing

AGENT = "inquiry"

# niyat pehchano (abhi keywords se; baad mein LLM hook lagega)
INTENTS = [
    ("greeting",   [r"\b(salam|assalam|hello|hi|aoa)\b"]),
    ("thanks",     [r"\b(shukriya|thanks|meherbani|jazak)\b"]),
    ("balance",    [r"(udhaar|baqaya|balance|hisab|khata|dena hai|lena hai)"]),
    ("discount",   [r"(discount|riayat|kam karo|rate kam|concession)"]),
    ("order",      [r"(chahiye|de do|bhej do|order|book|kitne piece|kitna maal)"]),
    ("product",    [r"(rate|qeemat|price|kimat|kya rate|bulb|wire|fan|switch|light|panel|cable|driver|sheet)"]),
]


def classify(text):
    t = text.lower()
    for intent, pats in INTENTS:
        for p in pats:
            if re.search(p, t):
                return intent
    return "unknown"


def reply_greeting(customer):
    name = customer["name"] if customer else "bhai"
    return (f"Assalam-o-Alaikum {name}! Imran Electric Store mein khush aamdeed. "
            "Kis product ka rate poochna hai?")


def reply_product(ctx, qty=1):
    p = ctx["product"]
    if not p:
        return "Maazrat, ye product hamari list mein nahi mila. Product ka naam dobara batayein?"
    q = pricing.quote(ctx["customer"]["id"] if ctx["customer"] else 1,
                      p["id"], qty, by="inquiry")
    if not q["ok"]:
        return f"Maazrat, {p['name']} ka rate abhi tay nahi ho saka."
    lines = [f"{p['name']} ({p['detail']})" if p["detail"] else p["name"]]
    lines.append(f"Rate: Rs {q['unit_rate']}" + (f" x {qty} = Rs {q['total']}" if qty > 1 else ""))
    if ctx["stock"] <= 0:
        lines.append("Note: stock abhi khatam hai — order par mangwana parega.")
    elif ctx["stock"] < 10:
        lines.append(f"Note: stock mein sirf {ctx['stock']} piece hain.")
    if ctx["last_rate"] and ctx["last_rate"]["quoted_rate"] != q["unit_rate"]:
        lines.append(f"(Pehli baar aapko Rs {ctx['last_rate']['quoted_rate']} par diya tha.)")
    return "\n".join(lines)


def reply_balance(ctx):
    if not ctx["customer"]:
        return "Aapka khata hamare record mein nahi mila."
    b = ctx["outstanding"]
    if b > 0:
        return f"{ctx['customer']['name']}: aapka baqaya Rs {b} hai."
    return f"{ctx['customer']['name']}: aapka khata clear hai, koi baqaya nahi."


def handle(customer_id, product_id, text):
    """Ek inquiry sambhalo. Returns Roman Urdu jawab."""
    intent = classify(text)
    if intent == "greeting":
        from tools.db import connect
        con = connect()
        cust = con.execute("SELECT * FROM customers WHERE id=?",
                           (customer_id,)).fetchone() if customer_id else None
        con.close()
        return reply_greeting(dict(cust) if cust else None)
    if intent in ("product", "order", "discount"):
        if not product_id:
            cands = pricing.find_product(text)
            if not cands:
                return "Kaunsa product? Naam batayein (masalan: 12W bulb, 3/29 wire)."
            if cands[0]["_score"] >= 2 or len(cands) == 1:
                product_id = cands[0]["id"]
            else:
                names = ", ".join(c["name"] for c in cands[:4])
                return f"Kayi products mile: {names}. Kaunsa wala?"
        # quantity: sirf tab jab adad wala lafz ho (12W ka 12 nahi!)
        m = __import__("re").search(
            r"(\d+)\s*(piece|pieces|pc|pcs|dana|nag|adad|darjan|dozen)\b", text.lower())
        qty = int(m.group(1)) if m and int(m.group(1)) < 100000 else 1
        ctx = gather_inquiry_context(AGENT, customer_id, product_id)
        return reply_product(ctx, qty)
    if intent == "balance":
        ctx = gather_inquiry_context(AGENT, customer_id, product_id or 0)
        return reply_balance(ctx)
    if intent == "thanks":
        return "Khush aamdeed! Aur kuch chahiye to batayein."
    # unknown bhi ho to product dhoondhne ki koshish (typo ho sakta hai)
    if intent == "unknown":
        cands = pricing.find_product(text)
        if cands and (cands[0]["_score"] >= 2 or len(cands) == 1):
            ctx = gather_inquiry_context(AGENT, customer_id, cands[0]["id"])
            return reply_product(ctx, 1)
    return ("Samajh nahi aaya. Aap product ka rate pooch sakte hain, "
            "order de sakte hain, ya apna baqaya pooch sakte hain.")
