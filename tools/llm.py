"""llm.py — Free Gemini model (AI Studio) ka client.
BMS me AI wali samajh ke liye. Key env var GEMINI_API_KEY me.
"""
import json
import os
import urllib.request
import urllib.error

MODEL = "gemini-3-flash-preview"
BASE = "https://generativelanguage.googleapis.com/v1beta/models"


def _key():
    return os.environ.get("GEMINI_API_KEY", "")


def ask(prompt, max_tokens=500):
    """Gemini se sawal pucho. Jawab text me ya None (fail par)."""
    key = _key()
    if not key:
        return None
    url = f"{BASE}/{MODEL}:generateContent?key={key}"
    data = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": max_tokens},
    }).encode()
    req = urllib.request.Request(url, data=data,
                                 headers={"Content-Type": "application/json"})
    try:
        resp = urllib.request.urlopen(req, timeout=45)
        d = json.loads(resp.read())
        parts = d["candidates"][0]["content"].get("parts", [])
        texts = [p.get("text", "") for p in parts if p.get("text")]
        return "".join(texts).strip() or None
    except Exception:
        return None


def shop_assistant(user_msg, shop_context=""):
    """Dukaan ke MAALIK (Azhar) ke assistant ke tor par jawab do (Roman Urdu).
    Ye chat customer ke liye NAHI — Azhar apne agents ko yahan se hukam deta hai."""
    prompt = (
        "Tum Imran Electric Store (Mandian, Abbottabad) ke AI assistant 'Munshi' ho. "
        "Tum se baat karne wala CUSTOMER nahi, dukaan ka MAALIK Azhar hai — "
        "woh tumhe aur tumhare 12 agents ko hukam deta hai. "
        "Hamesha Roman Urdu me jawab do, mukhtasir aur kaam ki baat. "
        "Qeematein aur stock ke bare me sirf wohi batao jo context me diya gaya hai — guess mat karo.\n\n"
        f"Context: {shop_context}\n\n"
        f"Azhar (maalik): {user_msg}\nMunshi:"
    )
    return ask(prompt)
