"""test_phase4.py — Inventory, Billing, Ledger, Supplier, Staff, Reports."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools import inventory, billing, ledger
from agents import manager, supplier_agent, staff_agent, reports_agent
from agents.base import can_write
from tools.db import connect

def check(name, cond):
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        raise SystemExit(f"FAILED: {name}")

# --- inventory ---
before = inventory.get_stock(30)
r = inventory.stock_in(30, 100, purchase_rate=120, by="test")
check("stock in 100", r["ok"] and r["new_stock"] == before + 100)
check("get_stock barha", inventory.get_stock(30) == before + 100)

# --- billing: 10 bulbs @ 150 = 1500, profit (150-120)*10=300 ---
b = billing.create_invoice(1, [(30, 10)], by="test")
check("bill bana", b["ok"])
check("bill total 1500", b["total"] == 1500)
check("bill profit 300", b["profit"] == 300)
check("stock ghata 10", inventory.get_stock(30) == before + 90)
check("ledger sale darj", ledger.outstanding(1) == 2500 + 1500)

# stock se zyada bill → mana
b2 = billing.create_invoice(1, [(30, 9999)], by="test")
check("zyada qty mana", not b2["ok"])

# --- ledger: payment 1000 ---
p = ledger.record_payment(1, 1000, note="test", by="test")
check("payment ok", p["ok"])
check("baqaya 3000", p["new_outstanding"] == 3000)

# --- supplier: draft + task ---
s = supplier_agent.find_supplier(30)
check("supplier mila", s is not None)
print("  supplier:", s["name"] if s else None)
d = supplier_agent.rate_request_draft(30, 50)
check("draft bana", "Imran Electric Store" in d)
t = supplier_agent.create_purchase_task(30, 50, by="test")
check("purchase task", t["ok"])
u = supplier_agent.update_task(t["task_id"], "assigned", by="test")
check("task assigned", u["ok"] and "assigned" in u["msg"])

# --- staff ---
s2 = staff_agent.handle("task dukaan ki safai", by="test")
check("staff task bani", "ban gayi" in s2)

# --- reports ---
rep = reports_agent.handle("report")
check("daily brief", "Aaj ki report" in rep)
print("  brief:", rep.replace("\n", " | ")[:160])

# --- manager routing ---
check("route bill", manager.route("bill 1 30:5")[0] == "billing")
check("route payment", manager.route("payment 1 500")[0] == "ledger")
check("route stock", manager.route("low stock")[0] == "inventory")
check("route report", manager.route("aaj ki report")[0] == "reports")

# --- safai ---
con = connect()
con.execute("DELETE FROM invoice_items WHERE invoice_id IN (SELECT id FROM invoices WHERE by='test')")
con.execute("DELETE FROM invoices WHERE by='test'")
con.execute("DELETE FROM payments WHERE note='test'")
con.execute("DELETE FROM ledger_entries WHERE note='test' OR ref LIKE 'INV-%' AND customer_id=1 AND kind='sale' AND id > 1")
con.execute("UPDATE stock SET quantity=0 WHERE product_id=30")
con.execute("DELETE FROM stock_moves WHERE product_id=30")
con.execute("DELETE FROM tasks WHERE id IN (SELECT ref_id FROM audit_log WHERE by_agent='test' AND tbl='tasks')")
con.execute("DELETE FROM audit_log WHERE by_agent='test'")
con.commit(); con.close()
check("cleanup", True)
print("\nSab Phase 4 tests kamyab!")
