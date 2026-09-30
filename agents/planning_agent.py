"""planning_agent.py — Purchase Planning Agent.

Low/zero stock dekh kar order list banata hai:
  kaunsa product, kitna mangwana hai, kis supplier se, aakhri khareed rate kya tha.
"""
from tools.db import connect
from tools import inventory
from agents.supplier_agent import find_supplier, create_purchase_task
import tools.pricing as pricing

AGENT = "planning"

# kitna stock hona chahiye (target) — product-wise badal sakta hai baad mein
TARGET_STOCK = 50


def order_list():
    """Order ki tajweez. Returns list of dicts."""
    items = []
    for i in inventory.low_stock(TARGET_STOCK):
        pid = i["id"]
        need = TARGET_STOCK - i["quantity"]
        s = find_supplier(pid)
        items.append({
            "product_id": pid,
            "name": i["name"],
            "detail": i["detail"],
            "have": i["quantity"],
            "need": need,
            "supplier": s["name"] if s else "unknown",
            "supplier_wa": s["whatsapp"] if s else None,
            "last_rate": pricing.purchase_rate(pid),
        })
    return items


def handle(text, by="Azhar"):
    t = text.lower()
    if "order" in t and "banao" in t:
        # purchase tasks banao
        made = []
        for o in order_list()[:10]:
            r = create_purchase_task(o["product_id"], o["need"], by=by)
            if r["ok"]:
                made.append(f"#{r['task_id']}")
        return f"{len(made)} purchase tasks ban gayin: {', '.join(made)}." if made else "Koi order ki zaroorat nahi."
    items = order_list()
    if not items:
        return "Sab ka stock theek hai — koi order ki zaroorat nahi."
    lines = [f"Order list ({len(items)} products):"]
    for o in items[:15]:
        lines.append(
            f"- {o['name']}: {o['have']} hain, {o['need']} mangwao | "
            f"{o['supplier']} (Rs {o['last_rate']})")
    if len(items) > 15:
        lines.append(f"... aur {len(items)-15} aur")
    lines.append("Tasks banane ke liye: 'order banao'")
    return "\n".join(lines)
