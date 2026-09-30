"""db.py — SQLite helper. Har tool yahi istemal karega."""
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "db", "shop.db")

def connect():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con

def now_pk():
    from datetime import datetime, timezone, timedelta
    pkt = timezone(timedelta(hours=5))
    return datetime.now(pkt).strftime("%Y-%m-%d %H:%M:%S")
