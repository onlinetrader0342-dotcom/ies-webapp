"""inventory_agent.py — Stock Agent. Maal aana/jaana, alerts."""
from agents.base import audit
from tools import inventory
import tools.pricing as pricing

AGENT = "inventory"


def handle(text, by="Azhar"):
    t = text.lower()
    import re
    # "stock in <product_id> <qty> <rate>"
    m = re.search(r"stock in (\d+)\s+(\d+)(?:\s+(\d+))?", t)
    if m:
        pid, qty = int(m.group(1)), int(m.group(2))
        rate = int(m.group(3)) if m.group(3) else None
        r = inventory.stock_in(pid, qty, purchase_rate=rate, by=by)
        if not r["ok"]:
            return f"Masla: {r['error']}"
        p = pricing.get_product(pid)
        return f"Stock in: {p['name']} +{qty} = {r['new_stock']} available."
    if "low stock" in t or "kam stock" in t or "stock alert" in t:
        items = inventory.low_stock()
        if not items:
            return "Sab products ka stock theek hai."
        lines = ["Kam stock wale products:"]
        for i in items[:15]:
            lines.append(f"- {i['name']}: {i['quantity']} bacha")
        return "\n".join(lines)
    if "stock" in t:
        # product dhoondho
        cands = pricing.find_product(t)
        if cands and cands[0]["_score"] >= 2:
            p = cands[0]
            q = inventory.get_stock(p["id"])
            return f"{p['name']}: stock mein {q} piece."
        return "Kaunse product ka stock? Naam batayein."
    return "Stock ke liye: 'stock in <id> <qty> <rate>', 'low stock', ya product ka naam."


def check_alerts():
    """Low/zero stock alerts — Manager roz chalaye."""
    zero = inventory.zero_stock()
    low = [i for i in inventory.low_stock() if i["quantity"] > 0]
    msgs = []
    if zero:
        msgs.append(f"KHATAM ({len(zero)}): " + ", ".join(i["name"] for i in zero[:5]))
    if low:
        msgs.append(f"KAM ({len(low)}): " + ", ".join(
            f"{i['name']}({i['quantity']})" for i in low[:5]))
    return msgs
