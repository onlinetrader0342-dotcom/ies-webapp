"""test_pricing.py — pricing engine ke tests (deterministic)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools import pricing
from tools.db import connect

def check(name, cond):
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        raise SystemExit(f"FAILED: {name}")

# 12W bulb: purchase 120 → default 20% → roundup10(144) = 150
q = pricing.quote(1, 30, 1, by="test")
check("default quote ok", q["ok"])
check("12W bulb unit 150", q["unit_rate"] == 150)
check("purchase rate 120", q["purchase_rate"] == 120)
check("default margin applied", q["applied"]["kind"] == "default_margin")

# qty total
q2 = pricing.quote(1, 30, 10, by="test")
check("10 piece total 1500", q2["total"] == 1500)

# customer margin rule: Atif (id 1) ko 10% margin
r = pricing.set_rule(customer_id=1, rule_type="margin_pct", margin_pct=10.0, by="test")
check("rule created", r["ok"])
q3 = pricing.quote(1, 30, 1, by="test")
check("10% margin → 140", q3["unit_rate"] == 140)  # roundup10(132)=140
check("margin rule applied", q3["applied"]["kind"] == "margin_pct")

# customer+product fixed special: Rs 105 (Azhar ki example)
r2 = pricing.set_rule(customer_id=1, product_id=30, rule_type="fixed_rate",
                      fixed_rate=105, scope="customer_product", by="test")
check("special rule created", r2["ok"])
q4 = pricing.quote(1, 30, 1, by="test")
check("special fixed 105 → roundup10 = 110", q4["unit_rate"] == 110)
check("fixed rule wins over margin", q4["applied"]["kind"] == "fixed_rate")

# last_rate history
lr = pricing.last_rate(1, 30)
check("last_rate milta hai", lr is not None and lr["quoted_rate"] == 110)

# safai: test rules hatao
con = connect()
con.execute("DELETE FROM pricing_rules WHERE created_by='test'")
con.execute("DELETE FROM rate_history WHERE by='test'")
con.commit(); con.close()
check("cleanup ok", True)

print("\nSab tests kamyab!")
