"""billing_agent.py — Billing/Sales Agent. Bill banao."""
from agents.base import audit, can_write
from tools import billing
import tools.pricing as pricing

AGENT = "billing"


def handle(customer_id, text, by="Azhar"):
    """Format: 'bill <customer_id> <product_id>:<qty> <product_id>:<qty> ...'
    Masalan: bill 1 30:10 31:5"""
    import re
    m = re.search(r"bill\s+(\d+)\s+(.+)", text.lower())
    if not m:
        return "Bill ke liye: 'bill <customer_id> <product_id>:<qty> ...' (masalan: bill 1 30:10)"
    cid = int(m.group(1))
    items = []
    for part in m.group(2).split():
        mm = re.match(r"(\d+):(\d+)", part)
        if mm:
            items.append((int(mm.group(1)), int(mm.group(2))))
    if not items:
        return "Koi item nahi mila. Format: bill 1 30:10"
    if not can_write(AGENT, "invoices"):
        return "Permission nahi."
    r = billing.create_invoice(cid, items, by=by)
    if not r["ok"]:
        return f"Bill nahi bana: {r['error']}"
    lines = [f"Bill #{r['invoice_id']} — Total Rs {r['total']} (profit Rs {r['profit']})"]
    for q in r["lines"]:
        lines.append(f"- {q['product']}: {q['qty']} x Rs {q['unit_rate']} = Rs {q['total']}")
    if "pdf" in text.lower():
        from tools import pdfbill
        p = pdfbill.make_pdf(r["invoice_id"])
        if p["ok"]:
            lines.append(f"PDF: {p['path']}")
    return "\n".join(lines)


def today_summary():
    s = billing.today_sales()
    return f"Aaj: {s['bills']} bill, sale Rs {s['total']}, profit Rs {s['profit']}."
