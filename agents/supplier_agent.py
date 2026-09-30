"""supplier_agent.py — Supplier Agent.

Kaam:
- product ke liye sahi supplier dhoondhna (keywords se)
- rate request ka draft banana (Azhar bhejega — agent khud nahi bhejta)
- emergency purchase task banana (status workflow ke saath)
"""
from tools.db import connect, now_pk
from agents.base import audit
import tools.pricing as pricing

AGENT = "supplier"

TASK_STATUSES = ["pending", "assigned", "in_progress", "collected", "received", "completed"]


def find_supplier(product_id):
    """Product ke keywords se supplier match karo."""
    p = pricing.get_product(product_id)
    if not p:
        return None
    text = f"{p['name']} {p['detail']} {p['brand']}".lower()
    con = connect()
    try:
        best, best_score = None, 0
        for s in con.execute("SELECT * FROM suppliers").fetchall():
            kws = (s["keywords"] or "").lower().replace(",", " ").split()
            score = sum(1 for k in kws if k and k in text)
            if s["deals"] and s["deals"].lower() in text:
                score += 2
            if score > best_score:
                best, best_score = dict(s), score
        return best
    finally:
        con.close()


def rate_request_draft(product_id, qty=1):
    """Supplier ko bhejne ke liye draft (Azhar approve karke bhejega)."""
    p = pricing.get_product(product_id)
    s = find_supplier(product_id)
    if not p:
        return "Product nahi mila."
    if not s:
        return f"{p['name']} ke liye koi supplier match nahi hua."
    draft = (f"Assalam-o-Alaikum {s['name']}! {p['name']} "
             f"({p['detail']}) {qty} piece ka rate aur availability batayein. "
             "- Imran Electric Store")
    return f"Supplier: {s['name']} ({s['whatsapp']})\nDraft:\n{draft}"


def create_purchase_task(product_id, qty, by="Azhar"):
    """Emergency purchase task (status: pending → ... → completed)."""
    p = pricing.get_product(product_id)
    s = find_supplier(product_id)
    con = connect()
    try:
        cur = con.execute(
            """INSERT INTO tasks (title, status, detail, created_at, updated_at)
               VALUES (?,?,?,?,?)""",
            (f"Purchase: {p['name']} x{qty}",
             "pending",
             f"supplier: {s['name'] if s else 'unknown'}",
             now_pk(), now_pk()))
        con.commit()
        tid = cur.lastrowid
    finally:
        con.close()
    audit(by, "create_purchase_task", "tasks", tid, new=f"{p['name']} x{qty}")
    return {"ok": True, "task_id": tid,
            "msg": f"Task #{tid}: {p['name']} x{qty} — status: pending"}


def update_task(task_id, status, staff_id=None, by="Azhar"):
    if status not in TASK_STATUSES:
        return {"ok": False, "error": f"status {TASK_STATUSES} mein se ho"}
    con = connect()
    try:
        old = con.execute("SELECT status FROM tasks WHERE id=?", (task_id,)).fetchone()
        if not old:
            return {"ok": False, "error": "task nahi mili"}
        con.execute(
            "UPDATE tasks SET status=?, assigned_to=COALESCE(?,assigned_to), updated_at=? WHERE id=?",
            (status, staff_id, now_pk(), task_id))
        con.commit()
    finally:
        con.close()
    audit(by, "update_task", "tasks", task_id, old=old["status"], new=status)
    return {"ok": True, "msg": f"Task #{task_id}: {old['status']} → {status}"}


def pending_tasks():
    con = connect()
    try:
        return [dict(r) for r in con.execute(
            "SELECT * FROM tasks WHERE status != 'completed' ORDER BY created_at DESC")]
    finally:
        con.close()
