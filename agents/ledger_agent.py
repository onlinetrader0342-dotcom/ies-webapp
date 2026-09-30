"""ledger_agent.py — Customer Ledger Agent."""
from agents.base import can_write
from tools import ledger
from tools.db import connect

AGENT = "ledger"


def handle(customer_id, text, by="Azhar"):
    import re
    t = text.lower()
    # "payment <customer_id> <amount>"
    m = re.search(r"payment\s+(\d+)\s+(\d+)", t)
    if m:
        if not can_write(AGENT, "payments"):
            return "Permission nahi."
        cid, amt = int(m.group(1)), int(m.group(2))
        r = ledger.record_payment(cid, amt, by=by)
        if not r["ok"]:
            return f"Masla: {r['error']}"
        return f"Payment darj: Rs {amt}. Baqaya ab Rs {r['new_outstanding']}."
    # "khata <customer_id>"
    m = re.search(r"khata\s+(\d+)", t)
    if m or "hisab" in t or "udhaar" in t:
        cid = int(m.group(1)) if m else customer_id
        if not cid:
            return "Kaunsa customer? 'khata <id>' likhein."
        con = connect()
        cust = con.execute("SELECT name FROM customers WHERE id=?", (cid,)).fetchone()
        con.close()
        name = cust["name"] if cust else f"#{cid}"
        bal = ledger.outstanding(cid)
        hist = ledger.history(cid, 5)
        lines = [f"{name} ka khata — Baqaya: Rs {bal}"]
        for h in hist:
            lines.append(f"  {h['at'][:10]} {h['kind']}: Rs {h['amount']} {h['note'] or ''}")
        return "\n".join(lines)
    return "Ledger: 'payment <customer_id> <raqam>' ya 'khata <customer_id>'."
