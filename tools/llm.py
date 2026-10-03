"""llm.py — Gemini free model se mukammal AI agent (function calling).

Ab TAMAM jawab LLM deta hai. Hisab-kitab ke liye tools hain jo asal
database se data nikalte hain — taake rate/stock ghalat na bataye.
"""
import json
import os
import urllib.request

MODEL = "gemini-3-flash-preview"
BASE = "https://generativelanguage.googleapis.com/v1beta/models"

SYSTEM = (
    "Tum Imran Electric Store (Mandian, Abbottabad) ke AI assistant 'Munshi' ho. "
    "Tum se baat karne wala CUSTOMER nahi, dukaan ka MAALIK Azhar hai — "
    "woh tumhe hukam deta hai. Hamesha Roman Urdu me, mukhtasir jawab do. "
    "Qeemat/stock/khata ke liye HAMESHA tools use karo — apne zehan se rate kabhi mat banao. "
    "Agar product na mile to tools ke result ke mutabiq batao, andaza mat lagao."
)

# ---------- Tool implementations (asal database se) ----------

def _t_product_rate(product_name):
    from tools import pricing
    from tools.db import connect
    cands = pricing.find_product(product_name)
    if not cands:
        return {"found": False, "msg": "Product nahi mila"}
    p = cands[0]
    # Read-only rate (bina history likhe)
    prate = pricing.purchase_rate(p["id"])
    if prate is None:
        return {"found": True, "name": p["name"], "rate": None,
                "msg": "Purchase rate darj nahi"}
    unit = pricing.roundup10(prate * 1.20)  # default 20% margin
    con = connect()
    try:
        s = con.execute("SELECT quantity FROM stock WHERE product_id=?",
                        (p["id"],)).fetchone()
        stock = s["quantity"] if s else 0
    finally:
        con.close()
    return {"found": True, "name": p["name"], "detail": p.get("detail", ""),
            "rate": unit, "stock": stock}


def _t_customer_khata(customer_name):
    from tools.db import connect
    con = connect()
    try:
        c = con.execute("SELECT * FROM customers WHERE name LIKE ?",
                        (f"%{customer_name}%",)).fetchone()
        if not c:
            return {"found": False}
        bal = con.execute(
            "SELECT COALESCE(SUM(amount),0) b FROM ledger WHERE customer_id=?",
            (c["id"],)).fetchone()["b"]
        return {"found": True, "name": c["name"], "balance": bal}
    finally:
        con.close()


def _t_make_bill(items):
    """items: [{'product': '12W bulb', 'qty': 2}]. Walk-in (id 2) par bill."""
    from tools import pricing, billing
    inv_items = []
    for it in items:
        cands = pricing.find_product(it["product"])
        if not cands:
            return {"ok": False, "msg": f"Product nahi mila: {it['product']}"}
        inv_items.append((cands[0]["id"], int(it.get("qty", 1))))
    b = billing.create_invoice(2, inv_items, by="Azhar-ai")
    if not b.get("ok"):
        return {"ok": False, "msg": b.get("error", "Bill nahi ban saka")}
    return {"ok": True, "bill_id": b.get("invoice_id"), "total": b.get("total")}


def _t_add_expense(amount, note):
    from tools import expenses
    expenses.add_expense("general", amount, note, by="Azhar-ai")
    return {"ok": True}


def _t_daily_report():
    from agents import reports_agent
    return {"report": reports_agent.daily_brief()}


def _t_low_stock():
    from tools.db import connect
    con = connect()
    try:
        rows = con.execute(
            """SELECT p.name, s.quantity FROM stock s
               JOIN products p ON p.id=s.product_id
               WHERE s.quantity<=10 ORDER BY s.quantity LIMIT 10""").fetchall()
        return [{"name": r["name"], "qty": r["quantity"]} for r in rows]
    finally:
        con.close()


TOOLS = {
    "product_rate": (_t_product_rate, {"product_name": "str"}),
    "customer_khata": (_t_customer_khata, {"customer_name": "str"}),
    "make_bill": (_t_make_bill, {"items": "list"}),
    "add_expense": (_t_add_expense, {"amount": "number", "note": "str"}),
    "daily_report": (_t_daily_report, {}),
    "low_stock": (_t_low_stock, {}),
}

GEMINI_TOOLS = [{
    "functionDeclarations": [
        {"name": "product_rate",
         "description": "Kisi product ka rate aur stock maloom karo",
         "parameters": {"type": "object",
                        "properties": {"product_name": {"type": "string"}},
                        "required": ["product_name"]}},
        {"name": "customer_khata",
         "description": "Customer ka udhaar balance maloom karo",
         "parameters": {"type": "object",
                        "properties": {"customer_name": {"type": "string"}},
                        "required": ["customer_name"]}},
        {"name": "make_bill",
         "description": "Bill banao. items: [{product, qty}]",
         "parameters": {"type": "object",
                        "properties": {"items": {"type": "array", "items": {
                            "type": "object",
                            "properties": {"product": {"type": "string"},
                                           "qty": {"type": "number"}}}}},
                        "required": ["items"]}},
        {"name": "add_expense",
         "description": "Kharcha darj karo",
         "parameters": {"type": "object",
                        "properties": {"amount": {"type": "number"},
                                       "note": {"type": "string"}},
                        "required": ["amount", "note"]}},
        {"name": "daily_report",
         "description": "Aaj ki sale, kharcha, munafa ki report",
         "parameters": {"type": "object", "properties": {}}},
        {"name": "low_stock",
         "description": "Kam stock wale products ki list",
         "parameters": {"type": "object", "properties": {}}},
    ]
}]


_last_error = None  # aakhri API nakami ki wajah (diagnostic ke liye)


def _call_api(payload, retries=1):
    global _last_error
    import time
    import urllib.error
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        _last_error = "no_key"
        return None
    url = f"{BASE}/{MODEL}:generateContent?key={key}"
    for attempt in range(retries + 1):
        req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                     headers={"Content-Type": "application/json"})
        try:
            resp = urllib.request.urlopen(req, timeout=25)
            _last_error = None
            return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            _last_error = f"http_{e.code}"
            if e.code == 429 and attempt < retries:
                time.sleep(10)  # mukhtasir wait, phir aik retry
                continue
            return None
        except TimeoutError:
            _last_error = "timeout_25s"
            return None
        except Exception as e:
            _last_error = f"network_{type(e).__name__}"
            return None
    _last_error = "retries_exhausted"
    return None


def agent_reply(user_msg, max_rounds=4):
    """Mukammal AI agent: tools ke saath jawab. Sirf LLM bolta hai."""
    contents = [{"role": "user", "parts": [{"text": user_msg}]}]
    for _ in range(max_rounds):
        d = _call_api({
            "systemInstruction": {"parts": [{"text": SYSTEM}]},
            "contents": contents,
            "tools": GEMINI_TOOLS,
            "generationConfig": {"maxOutputTokens": 2000},
        })
        if not d:
            return None
        cand = d["candidates"][0]
        parts = cand["content"].get("parts", [])
        contents.append({"role": "model", "parts": parts})

        fns = [p["functionCall"] for p in parts if "functionCall" in p]
        if not fns:
            texts = [p.get("text", "") for p in parts if p.get("text")]
            return "".join(texts).strip() or None

        # Tools chalao aur result wapas bhejo
        tool_parts = []
        for fc in fns:
            name, args = fc["name"], fc.get("args", {})
            fn, _ = TOOLS.get(name, (None, None))
            try:
                result = fn(**args) if fn else {"error": "unknown tool"}
            except Exception as e:
                result = {"error": str(e)[:100]}
            tool_parts.append({
                "functionResponse": {"name": name,
                                     "response": {"result": result}}})
        contents.append({"role": "user", "parts": tool_parts})
    return None


# Purana simple fallback (agar agent_reply fail ho)
def ask(prompt, max_tokens=500):
    d = _call_api({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": max_tokens},
    })
    if not d:
        return None
    try:
        parts = d["candidates"][0]["content"].get("parts", [])
        texts = [p.get("text", "") for p in parts if p.get("text")]
        return "".join(texts).strip() or None
    except Exception:
        return None


def shop_assistant(user_msg, shop_context=""):
    prompt = (SYSTEM + f"\n\nContext: {shop_context}\n\n"
              f"Azhar (maalik): {user_msg}\nMunshi:")
    return ask(prompt)
