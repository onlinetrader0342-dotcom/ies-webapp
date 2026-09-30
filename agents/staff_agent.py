"""staff_agent.py — Staff Tasks Agent (assignment, progress, delay)."""
from tools.db import connect, now_pk
from agents.base import audit
from agents.supplier_agent import update_task, pending_tasks, TASK_STATUSES

AGENT = "staff"


def handle(text, by="Azhar"):
    import re
    t = text.lower()
    # "task <title>" → nayi task
    m = re.search(r"^task\s+(.+)", t)
    if m and "status" not in t:
        con = connect()
        try:
            cur = con.execute(
                "INSERT INTO tasks (title, status, created_at, updated_at) VALUES (?,?,?,?)",
                (m.group(1), "pending", now_pk(), now_pk()))
            con.commit()
            tid = cur.lastrowid
        finally:
            con.close()
        audit(by, "create_task", "tasks", tid, new=m.group(1))
        return f"Task #{tid} ban gayi: {m.group(1)} (pending)"
    # "task status <id> <status>"
    m = re.search(r"task status (\d+)\s+(\w+)", t)
    if m:
        r = update_task(int(m.group(1)), m.group(2), by=by)
        return r.get("msg", r.get("error"))
    if "tasks" in t or "kaam" in t:
        tasks = pending_tasks()
        if not tasks:
            return "Koi pending task nahi."
        lines = ["Pending tasks:"]
        for x in tasks[:10]:
            lines.append(f"#{x['id']} [{x['status']}] {x['title']}")
        return "\n".join(lines)
    return "Tasks: 'task <kaam>', 'task status <id> <status>', ya 'tasks'."


def staff_list():
    con = connect()
    try:
        return [dict(r) for r in con.execute("SELECT * FROM staff")]
    finally:
        con.close()
