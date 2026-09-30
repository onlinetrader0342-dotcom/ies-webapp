"""pricing.py — Deterministic pricing engine.

SUNAHRA USOOL: qeemat hamesha yahan se aayegi. AI model kabhi khud
qeemat, discount ya total nahi banayega — sirf ye functions call karega.

Pricing hierarchy (oopar wala jeetta hai):
  1. temporary fixed rate (active, expiry na guzri ho) — customer+product par
  2. fixed_rate rule (customer + product specific special rate)
  3. margin_pct rule (customer + product specific)
  4. margin_pct rule (customer specific, sab products par)
  5. default: purchase_rate + 20% margin

Special products (is_special=1): NET rate — koi margin, koi discount nahi.
Sab rates Rs 10 par round-up.
"""
import math
from .db import connect, now_pk

DEFAULT_MARGIN_PCT = 20.0


def roundup10(x):
    return int(math.ceil(x / 10.0) * 10)


def purchase_rate(product_id):
    """Latest purchase rate. Koi row na ho to None."""
    con = connect()
    try:
        r = con.execute(
            "SELECT rate FROM purchase_rates WHERE product_id=? ORDER BY at DESC, id DESC LIMIT 1",
            (product_id,)).fetchone()
        return r["rate"] if r else None
    finally:
        con.close()


def get_product(product_id):
    con = connect()
    try:
        return con.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
    finally:
        con.close()


def find_product(text):
    """Naam/detail se product dhoondho. Har word ka score; behtareen match pehle.
    Typo-tolerant: difflib se ghalat likhe lafz theek karta hai (blub→bulb).
    Returns list of dicts with '_score'."""
    import difflib
    con = connect()
    try:
        import re as _re2
        # "12 w" → "12w" joro (sirf single-letter unit: W, V)
        text = _re2.sub(r"(\d+)\s+([a-zA-Z])(?![a-zA-Z])", r"\1\2", text.lower())
        words = [w for w in text.split() if len(w) > 2 or _re2.search(r"\d", w)]
        if not words:
            return []
        # vocabulary: products ke sab lafz (punctuation saaf karke)
        import re as _re
        vocab = set()
        for p in con.execute("SELECT name, detail FROM products").fetchall():
            for w in f"{p['name']} {p['detail']}".lower().split():
                w = _re.sub(r"[^a-z0-9/]", "", w)
                if len(w) > 2:
                    vocab.add(w)
        # typo theek karo
        fixed = []
        for w in words:
            if w in vocab:
                fixed.append(w)
            else:
                m = difflib.get_close_matches(w, vocab, n=1, cutoff=0.7)
                fixed.append(m[0] if m else w)
        scored = {}
        for w in fixed:
            for p in con.execute(
                    "SELECT * FROM products WHERE lower(name) LIKE ? OR lower(detail) LIKE ?",
                    (f"%{w}%", f"%{w}%")).fetchall():
                d = dict(p)
                key = d["id"]
                if key not in scored:
                    d["_score"] = 0
                    scored[key] = d
                scored[key]["_score"] += 1
        out = sorted(scored.values(), key=lambda d: -d["_score"])
        return out[:10]
    finally:
        con.close()


def _active_rules(customer_id, product_id):
    """Customer+product par laagoo active rules, priority order mein."""
    con = connect()
    try:
        now = now_pk()
        rows = con.execute(
            """SELECT * FROM pricing_rules
               WHERE active=1 AND starts_at <= ?
                 AND (ends_at IS NULL OR ends_at >= ?)
                 AND (customer_id IS NULL OR customer_id=?)
                 AND (product_id IS NULL OR product_id=?)
               ORDER BY
                 CASE rule_type WHEN 'temporary' THEN 0 WHEN 'fixed_rate' THEN 1 ELSE 2 END,
                 CASE WHEN customer_id IS NOT NULL AND product_id IS NOT NULL THEN 0
                      WHEN customer_id IS NOT NULL THEN 1 ELSE 2 END""",
            (now, now, customer_id, product_id)).fetchall()
        # sirf woh rules jo is customer/product par waqai laagoo hon
        out = []
        for r in rows:
            rc, rp = r["customer_id"], r["product_id"]
            if rc is not None and rc != customer_id:
                continue
            if rp is not None and rp != product_id:
                continue
            out.append(r)
        return out
    finally:
        con.close()


def quote(customer_id, product_id, qty=1, by="system"):
    """Mukammal quote. Returns dict with breakdown. History mein darj hota hai."""
    prod = get_product(product_id)
    if not prod:
        return {"ok": False, "error": "product nahi mila"}
    prate = purchase_rate(product_id)
    if prate is None:
        return {"ok": False, "error": "purchase rate darj nahi"}

    if prod["is_special"]:
        unit = roundup10(prate)
        applied = {"kind": "net", "detail": "special item — net rate, koi margin/discount nahi"}
    else:
        rules = _active_rules(customer_id, product_id)
        rule = rules[0] if rules else None
        if rule is None:
            unit = roundup10(prate * (1 + DEFAULT_MARGIN_PCT / 100))
            applied = {"kind": "default_margin", "margin_pct": DEFAULT_MARGIN_PCT,
                       "detail": f"default {DEFAULT_MARGIN_PCT}% margin"}
        elif rule["rule_type"] == "temporary":
            unit = roundup10(rule["fixed_rate"])
            applied = {"kind": "temporary", "rule_id": rule["id"],
                       "detail": f"temporary fixed Rs {rule['fixed_rate']}"}
        elif rule["rule_type"] == "fixed_rate":
            unit = roundup10(rule["fixed_rate"])
            applied = {"kind": "fixed_rate", "rule_id": rule["id"],
                       "detail": "customer+product special rate"}
        else:  # margin_pct
            unit = roundup10(prate * (1 + rule["margin_pct"] / 100))
            applied = {"kind": "margin_pct", "rule_id": rule["id"],
                       "margin_pct": rule["margin_pct"],
                       "detail": f"customer margin {rule['margin_pct']}%"}

    total = unit * qty
    result = {"ok": True, "product_id": product_id, "product": prod["name"], "detail": prod["detail"],
              "purchase_rate": prate, "unit_rate": unit, "qty": qty,
              "total": total, "applied": applied}

    # history darj karo
    con = connect()
    try:
        con.execute(
            "INSERT INTO rate_history (customer_id, product_id, quoted_rate, at, by)"
            " VALUES (?,?,?,?,?)",
            (customer_id, product_id, unit, now_pk(), by))
        con.commit()
    finally:
        con.close()
    return result


def set_rule(customer_id=None, product_id=None, rule_type="margin_pct",
             margin_pct=None, fixed_rate=None, scope="customer",
             ends_at=None, by="Azhar"):
    """Naya pricing rule banao. Purana same-scope rule auto-deactivate."""
    con = connect()
    try:
        if rule_type == "margin_pct" and margin_pct is None:
            return {"ok": False, "error": "margin_pct chahiye"}
        if rule_type in ("fixed_rate", "temporary") and fixed_rate is None:
            return {"ok": False, "error": "fixed_rate chahiye"}
        # purana active same-scope rule band karo
        con.execute(
            """UPDATE pricing_rules SET active=0
               WHERE active=1
                 AND COALESCE(customer_id,-1)=COALESCE(?,-1)
                 AND COALESCE(product_id,-1)=COALESCE(?,-1)
                 AND rule_type=?""",
            (customer_id, product_id, rule_type))
        cur = con.execute(
            """INSERT INTO pricing_rules
               (customer_id, product_id, rule_type, margin_pct, fixed_rate,
                scope, starts_at, ends_at, active, created_by, created_at)
               VALUES (?,?,?,?,?,?,?, ?,1,?,?)""",
            (customer_id, product_id, rule_type, margin_pct, fixed_rate,
             scope, now_pk(), ends_at, by, now_pk()))
        con.commit()
        return {"ok": True, "rule_id": cur.lastrowid}
    finally:
        con.close()


def last_rate(customer_id, product_id):
    """Is customer ko is product ka aakhri quoted rate kya tha?"""
    con = connect()
    try:
        r = con.execute(
            """SELECT quoted_rate, sale_rate, at, by FROM rate_history
               WHERE customer_id=? AND product_id=?
               ORDER BY at DESC, id DESC LIMIT 1""",
            (customer_id, product_id)).fetchone()
        return dict(r) if r else None
    finally:
        con.close()


if __name__ == "__main__":
    import sys, json
    # CLI: python -m tools.pricing quote <customer_id> <product_id> [qty]
    #      python -m tools.pricing find <text>
    #      python -m tools.pricing last <customer_id> <product_id>
    a = sys.argv[1:]
    if not a:
        print("usage: quote|find|last ...")
        sys.exit(2)
    if a[0] == "quote" and len(a) >= 3:
        q = int(a[3]) if len(a) > 3 else 1
        print(json.dumps(quote(int(a[1]), int(a[2]), q), ensure_ascii=False, indent=1))
    elif a[0] == "find" and len(a) >= 2:
        for p in find_product(" ".join(a[1:])):
            print(p["id"], "|", p["name"], "|", p["detail"], "|", p["brand"])
    elif a[0] == "last" and len(a) >= 3:
        print(json.dumps(last_rate(int(a[1]), int(a[2])), ensure_ascii=False))
    else:
        print("usage: quote|find|last ...")
