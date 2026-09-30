"""reports_agent.py — Reports / Decision Support. Roman Urdu mein.

Dashboard format: WHAT (yeh kya hai) / WHY (kyun important) /
CHANGE (kya badla) / IMPACT (business par effect) / ACTION (options).
"""
from tools.db import connect
from tools import billing, ledger, inventory

AGENT = "reports"


def daily_brief():
    """Roz ka mukhtasar brief — Roman Urdu."""
    s = billing.today_sales()
    low = inventory.low_stock()
    debts = ledger.all_outstanding()
    total_debt = sum(d["bal"] for d in debts)

    lines = ["*Aaj ki report*"]
    lines.append(f"WHAT: {s['bills']} bill, sale Rs {s['total']}, profit Rs {s['profit']}.")
    if s['bills'] == 0:
        lines.append("WHY: aaj koi sale nahi hui — dhyaan dena chahiye.")
    lines.append(f"CHANGE: {len(low)} products low/zero stock par hain.")
    lines.append(f"IMPACT: customers ka Rs {total_debt} udhaar baqaya hai.")
    acts = []
    if low:
        acts.append(f"{low[0]['name']} ka stock mangwao")
    if debts:
        acts.append(f"{debts[0]['name']} se Rs {debts[0]['bal']} recovery karo")
    if acts:
        lines.append("ACTION: " + " | ".join(acts))
    return "\n".join(lines)


def profit_report(days=7):
    from tools import expenses
    con = connect()
    try:
        r = con.execute(
            """SELECT COUNT(*) n, COALESCE(SUM(total),0) t, COALESCE(SUM(profit),0) p
               FROM invoices WHERE at >= datetime('now', ?)""",
            (f"-{days} days",)).fetchone()
        exp = expenses.total_expenses(days)
        return (f"Pichle {days} din: {r['n']} bill, sale Rs {r['t']}, "
                f"gross profit Rs {r['p']}, kharchay Rs {exp}, "
                f"ASAL MUNAFA Rs {r['p'] - exp}.")
    finally:
        con.close()


def handle(text):
    t = text.lower()
    if "profit" in t or "munafa" in t:
        import re
        m = re.search(r"(\d+)", t)
        return profit_report(int(m.group(1)) if m else 7)
    return daily_brief()
