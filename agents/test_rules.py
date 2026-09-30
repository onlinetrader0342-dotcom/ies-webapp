"""test_rules.py — Business Rules agent tests."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents import rules_agent, manager
import tools.pricing as pricing
from tools.db import connect

def check(name, cond):
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        raise SystemExit(f"FAILED: {name}")

# scope detection
check("global scope", rules_agent.detect_scope("jumme ko dukaan jaldi band")[0] == "global")
check("customer scope", rules_agent.detect_scope("atif ko udhaar do")[0] == "customer")
check("supplier temp", rules_agent.detect_scope("is hafte shahid se khareedna")[0] == "temporary")

# pricing vs business
check("pricing pehchana", rules_agent.is_pricing_rule("atif ko 10% riayat do"))
check("business pehchana", not rules_agent.is_pricing_rule("jumme ko dukaan jaldi band"))

# business rule add + list + remove
r1 = rules_agent.add_rule("jumme ko dukaan 2 baje band", by="test")
check("usool darj", "darj ho gaya" in r1)
print("  ", r1)
r2 = rules_agent.list_rules()
check("list mein hai", "jumme" in r2)
import re
mid = int(re.search(r"#(\d+)", r2).group(1))
r3 = rules_agent.remove_rule(mid, by="test")
check("usool hatao", "hata diya" in r3)

# pricing rule via natural language: "atif ko 10% riayat" → margin 10%
r4 = rules_agent.add_rule("atif ko hamesha 10% riayat do", by="test")
check("riayat rule", "Riayat lag gayi" in r4)
print("  ", r4)
q = pricing.quote(1, 30, 1, by="test")
check("quote ab 10% margin par", q["unit_rate"] == 140 and q["applied"]["kind"] == "margin_pct")

# manager routing
check("route usool", manager.route("usool banao test")[0] == "rules")
ans = manager.handle_message(None, "usool list")
check("manager se usool", "usool" in ans.lower() or "koi" in ans.lower())

# safai
con = connect()
con.execute("DELETE FROM pricing_rules WHERE created_by='test'")
con.execute("DELETE FROM business_rules WHERE created_by='test'")
con.execute("DELETE FROM rate_history WHERE by='test'")
con.execute("DELETE FROM audit_log WHERE by_agent='test'")
con.commit(); con.close()
check("cleanup", True)
print("\nSab rules tests kamyab!")
