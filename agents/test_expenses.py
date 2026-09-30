"""test_expenses.py — Kharchay tests."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools import expenses
from agents import manager, expense_agent
from tools.db import connect

def check(name, cond):
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        raise SystemExit(f"FAILED: {name}")

r = expenses.add_expense("bijli", 2000, note="test", by="test")
check("kharcha darj", r["ok"])
r2 = expenses.add_expense("kiraya", 15000, note="test", by="test")
check("dosra kharcha", r2["ok"])
check("total 17000", expenses.total_expenses(30) == 17000)

cats = expenses.by_category(30)
check("category breakdown", len(cats) >= 2)

# net profit = gross - expenses
np_ = expenses.net_profit(30)
check("net profit hisab", np_ == expenses.gross_profit(30) - 17000)

# agent
a1 = expense_agent.handle("kharcha transport 500 test", by="test")
check("agent kharcha", "darj" in a1)
a2 = manager.handle_message(None, "kharcha list")
check("manager kharcha list", "kharchay" in a2)
print("  ", a2.replace("\n", " | ")[:150])
a3 = manager.handle_message(None, "munafa")
check("munafa me asal", "ASAL MUNAFA" in a3)

# safai
con = connect()
con.execute("DELETE FROM expenses WHERE by='test'")
con.execute("DELETE FROM audit_log WHERE by_agent='test'")
con.commit(); con.close()
check("cleanup", True)
print("\nSab expense tests kamyab!")
