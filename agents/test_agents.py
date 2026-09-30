"""test_agents.py — Phase 3 tests."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents import manager, inquiry_agent, pricing_agent
from agents.base import can_read, can_write
from tools.db import connect

def check(name, cond):
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        raise SystemExit(f"FAILED: {name}")

# permissions
check("inquiry sirf read", can_read("inquiry", "products") and not can_write("inquiry", "pricing_rules"))
check("pricing write allowed", can_write("pricing", "pricing_rules"))

# intent classification
check("greeting", inquiry_agent.classify("Assalam o alaikum") == "greeting")
check("product", inquiry_agent.classify("12W bulb ka rate?") == "product")
check("balance", inquiry_agent.classify("mera udhaar kitna hai?") == "balance")

# manager routing
check("route product", manager.route("12W bulb rate")[0] == "inquiry")
check("route admin", manager.route("special rate 1 30 105")[0] == "pricing")

# end-to-end: 12W bulb inquiry (Atif id=1, product id=30)
ans = manager.handle_message(None, "12W bulb ka rate kya hai?")
check("jawab mein 150", "150" in ans)
print("  jawab:", ans.replace("\n", " | "))

# greeting
ans2 = manager.handle_message(None, "salam")
check("greeting jawab", "Assalam-o-Alaikum" in ans2)

# balance (Atif ka 2500 udhaar)
ans3 = inquiry_agent.handle(1, None, "mera baqaya kitna hai?")
check("baqaya 2500", "2500" in ans3)
print("  jawab:", ans3)

# pricing agent: special rate lagao → quote badal jaye
r = pricing_agent.set_special_rate(1, 30, 105, "test", by="test")
check("special rate set", r["ok"])
q = pricing_agent.quote_for(1, 30)
check("quote ab 110", q["unit_rate"] == 110)

# audit darj hua?
con = connect()
n = con.execute("SELECT COUNT(*) c FROM audit_log WHERE by_agent='test'").fetchone()["c"]
check("audit log mein entry", n >= 1)
# safai
con.execute("DELETE FROM pricing_rules WHERE created_by='test'")
con.execute("DELETE FROM rate_history WHERE by='test'")
con.execute("DELETE FROM audit_log WHERE by_agent='test'")
con.commit(); con.close()

print("\nSab agent tests kamyab!")
