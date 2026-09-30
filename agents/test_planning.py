"""test_planning.py — Purchase planning + PDF bill tests."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents import planning_agent, manager
from tools import billing, pdfbill, inventory
from tools.db import connect

def check(name, cond):
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        raise SystemExit(f"FAILED: {name}")

items = planning_agent.order_list()
check("order list bani", len(items) > 0)
o = items[0]
check("order fields", all(k in o for k in ("name", "need", "supplier", "last_rate")))
check("need positive", o["need"] > 0)
print(f"  misal: {o['name']} — {o['need']} mangwao, {o['supplier']} Rs {o['last_rate']}")

ans = manager.handle_message(None, "order list")
check("manager order", "Order list" in ans)
check("route planning", manager.route("order list")[0] == "planning")

# order banao → tasks
t = planning_agent.handle("order banao", by="test")
check("tasks bani", "purchase tasks" in t)
print("  ", t[:80])

# PDF bill
inventory.stock_in(30, 50, by="test")
b = billing.create_invoice(1, [(30, 2)], by="test")
p = pdfbill.make_pdf(b["invoice_id"])
check("PDF bana", p["ok"] and os.path.exists(p["path"]))
check("PDF size", os.path.getsize(p["path"]) > 500)

# safai
con = connect()
for iid in [b["invoice_id"]]:
    con.execute("DELETE FROM invoice_items WHERE invoice_id=?", (iid,))
    con.execute("DELETE FROM invoices WHERE id=?", (iid,))
    con.execute("DELETE FROM ledger_entries WHERE ref=?", (f"INV-{iid}",))
con.execute("UPDATE stock SET quantity=50 WHERE product_id=30")
con.execute("DELETE FROM stock_moves WHERE product_id=30")
con.execute("DELETE FROM purchase_rates WHERE note='test'")
con.execute("DELETE FROM tasks WHERE title LIKE 'Purchase:%'")
con.execute("DELETE FROM audit_log WHERE by_agent='test'")
con.commit(); con.close()
os.remove(p["path"])
check("cleanup", True)
print("\nSab planning/PDF tests kamyab!")
