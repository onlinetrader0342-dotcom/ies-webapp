"""expense_agent.py — Kharchay Agent."""
from agents.base import can_write
from tools import expenses

AGENT = "expense"


def handle(text, by="Azhar"):
    import re
    t = text.lower()
    # "kharcha <category> <amount> [note]"
    m = re.search(r"kharcha\s+(\w+)\s+(\d+)(?:\s+(.+))?", t)
    if m:
        if not can_write(AGENT, "expenses"):
            return "Permission nahi."
        r = expenses.add_expense(m.group(1), int(m.group(2)),
                                 m.group(3), by=by)
        if not r["ok"]:
            return f"Masla: {r['error']}"
        return f"Kharcha darj: {m.group(1)} Rs {m.group(2)}."
    if "kharcha" in t and ("list" in t or "dekho" in t or "kitna" in t):
        cats = expenses.by_category(30)
        if not cats:
            return "Pichle 30 din me koi kharcha darj nahi."
        lines = ["Pichle 30 din ke kharchay:"]
        for c in cats:
            lines.append(f"  - {c['category']}: Rs {c['t']}")
        lines.append(f"Asal munafa: Rs {expenses.net_profit(30)}")
        return "\n".join(lines)
    if "munafa" in t or "profit" in t:
        return expenses.summary(30)
    return ("Kharchay: 'kharcha <category> <raqam> [note]' — "
            "categories: kiraya, bijli, tankhwah, transport, chaay_pani, maintenance, tax, doosra. "
            "'kharcha list' se hisab dekho.")
