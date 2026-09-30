"""Imran Electric Store — Web App (Render deployment).
Dashboard + Munshi chat. Uses the existing agents/tools directly.
"""
import os, sys, json, sqlite3
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from flask import Flask, request, jsonify, render_template_string

from agents import manager
from tools.db import connect

app = Flask(__name__)

PAGE = """<!DOCTYPE html><html lang="ur"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Imran Electric Store</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:system-ui,'Segoe UI',sans-serif;background:#0f1a14;color:#f0f4f1;min-height:100vh}
header{background:linear-gradient(135deg,#14532d,#1a7a3c);padding:14px 16px;position:sticky;top:0;z-index:10;box-shadow:0 2px 12px rgba(0,0,0,.4)}
header h1{font-size:19px}header p{font-size:12px;opacity:.85}
nav{display:flex;gap:8px;padding:10px 12px;background:#0c130e;position:sticky;top:64px;z-index:9}
nav button{flex:1;padding:10px;border:none;border-radius:10px;background:#1c2b21;color:#d7e3da;font-size:14px;cursor:pointer}
nav button.on{background:#22a355;color:#fff;font-weight:700}
main{padding:12px;max-width:640px;margin:0 auto}
.cards{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:14px}
.card{background:#16241b;border:1px solid #24402e;border-radius:14px;padding:14px}
.card .lbl{font-size:12px;color:#9db8a5}.card .val{font-size:22px;font-weight:800;margin-top:4px;color:#ffd76a}
.card .val.green{color:#5be3a0}
table{width:100%;border-collapse:collapse;font-size:13px;background:#16241b;border-radius:12px;overflow:hidden}
th,td{padding:9px 8px;text-align:right;border-bottom:1px solid #223526}
th{background:#1b2f22;color:#9db8a5;font-weight:600}
td:first-child,th:first-child{text-align:left}
.sec{font-size:15px;font-weight:700;margin:16px 0 8px;color:#ffd76a}
#chatlog{height:52vh;overflow-y:auto;background:#101812;border-radius:14px;padding:12px;margin-bottom:10px;border:1px solid #24402e}
.msg{margin:8px 0;max-width:85%;padding:10px 12px;border-radius:14px;font-size:14px;line-height:1.5}
.me{background:#22a355;margin-left:auto;border-bottom-right-radius:4px}
.munshi{background:#1e2f24;border:1px solid #2c4636;border-bottom-left-radius:4px}
.row{display:flex;gap:8px}
#qin{flex:1;padding:12px;border-radius:12px;border:1px solid #2c4636;background:#101812;color:#fff;font-size:15px}
#qbtn{padding:12px 18px;border:none;border-radius:12px;background:#22a355;color:#fff;font-weight:700;font-size:15px}
.hidden{display:none}
.low{color:#ff8a8a;font-weight:700}
</style></head><body>
<header><h1>⚡ Imran Electric Store</h1><p>Mandian, Abbottabad — Munshi Dashboard</p></header>
<nav>
<button id="t-dash" class="on" onclick="tab('dash')">📊 Hisab</button>
<button id="t-stock" onclick="tab('stock')">📦 Maal</button>
<button id="t-chat" onclick="tab('chat')">💬 Munshi</button>
</nav>
<main>
<div id="p-dash">
  <div class="cards" id="cards"></div>
  <div class="sec">Atif ka Udhaar</div><div id="udhaar"></div>
  <div class="sec">Kam Stock (≤10)</div><div id="low"></div>
</div>
<div id="p-stock" class="hidden">
  <div class="sec">Products (100)</div>
  <input id="sbox" placeholder="🔍 Talaash..." oninput="fstock()" style="width:100%;padding:11px;border-radius:10px;border:1px solid #2c4636;background:#101812;color:#fff;margin-bottom:10px">
  <div id="stable"></div>
</div>
<div id="p-chat" class="hidden">
  <div id="chatlog"><div class="msg munshi">Walaikum Assalam Azhar bhai! Main Munshi hoon. Rate, stock, bill — jo puchna hai pucho.</div></div>
  <div class="row"><input id="qin" placeholder="Munshi se pucho..." onkeydown="if(event.key==='Enter')send()"><button id="qbtn" onclick="send()">Bhejo</button></div>
</div>
</main>
<script>
let STOCK=[];
function tab(t){['dash','stock','chat'].forEach(x=>{document.getElementById('p-'+x).classList.toggle('hidden',x!==t);document.getElementById('t-'+x).classList.toggle('on',x===t)})}
async function load(){let d=await(await fetch('/api/dashboard')).json();
document.getElementById('cards').innerHTML=
`<div class="card"><div class="lbl">Aaj ki Sale</div><div class="val">Rs ${d.today.total}</div></div>
<div class="card"><div class="lbl">Aaj ka Munafa</div><div class="val green">Rs ${d.today.net}</div></div>
<div class="card"><div class="lbl">Kul Maal (pieces)</div><div class="val">${d.stock.units}</div></div>
<div class="card"><div class="lbl">Stock Value</div><div class="val">Rs ${d.stock.value}</div></div>
<div class="card"><div class="lbl">Kul Udhaar</div><div class="val" style="color:#ff9a9a">Rs ${d.udhaarTotal}</div></div>
<div class="card"><div class="lbl">Products</div><div class="val">${d.stock.productCount}</div></div>`;
document.getElementById('udhaar').innerHTML=d.udhaar.length?`<table>${d.udhaar.map(u=>`<tr><td>${u.name}</td><td>Rs ${u.balance}</td></tr>`).join('')}</table>`:'<p style="color:#9db8a5">Koi udhaar nahi</p>';
document.getElementById('low').innerHTML=d.low.length?`<table>${d.low.map(p=>`<tr><td>${p.name}</td><td class="low">${p.qty}</td></tr>`).join('')}</table>`:'<p style="color:#9db8a5">Sab theek hai</p>';
STOCK=d.products;
fstock();}
function fstock(){let q=(document.getElementById('sbox').value||'').toLowerCase();
let rows=STOCK.filter(p=>(p.name+' '+p.detail).toLowerCase().includes(q)).slice(0,60);
document.getElementById('stable').innerHTML=`<table><tr><th>Product</th><th>Rate</th><th>Stock</th></tr>${rows.map(p=>`<tr><td>${p.name}<br><small style="color:#9db8a5">${p.detail||''}</small></td><td>Rs ${p.sale}</td><td class="${p.stock<=10?'low':''}">${p.stock}</td></tr>`).join('')}</table>`}
async function send(){let i=document.getElementById('qin'),t=i.value.trim();if(!t)return;i.value='';
let L=document.getElementById('chatlog');L.innerHTML+=`<div class="msg me">${t}</div>`;L.scrollTop=1e6;
let r=await(await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:t})})).json();
L.innerHTML+=`<div class="msg munshi">${r.reply}</div>`;L.scrollTop=1e6;load();}
load();
</script></body></html>"""

@app.get("/")
def home():
    return render_template_string(PAGE)

@app.get("/api/dashboard")
def api_dash():
    con = connect(); cur = con.cursor()
    prod = [dict(r) for r in cur.execute(
        """SELECT p.id,p.name,p.detail,p.brand,COALESCE(s.quantity,0) stock,
           (SELECT rate FROM purchase_rates pr WHERE pr.product_id=p.id ORDER BY pr.id DESC LIMIT 1) prate
           FROM products p LEFT JOIN stock s ON s.product_id=p.id ORDER BY p.id""")]
    for p in prod:
        r = p["prate"] or 0
        p["sale"] = ((r * 120 // 100) + 9) // 10 * 10  # +20%, round up 10
    units = sum(p["stock"] for p in prod)
    value = sum(p["stock"] * (p["prate"] or 0) for p in prod)
    low = [{"name": p["name"], "qty": p["stock"]} for p in prod if p["stock"] <= 10]
    today = cur.execute(
        "SELECT COALESCE(SUM(CASE WHEN kind='sale' THEN amount END),0) FROM ledger_entries WHERE date(at)=date('now','localtime')").fetchone()[0]
    udh = [dict(r) for r in cur.execute(
        """SELECT c.name, SUM(l.amount) balance FROM ledger_entries l
           JOIN customers c ON c.id=l.customer_id GROUP BY c.id HAVING SUM(l.amount)>0""")]
    con.close()
    return jsonify({
        "today": {"total": today or 0, "net": 0, "saleCount": 0},
        "stock": {"units": units, "value": value, "productCount": len(prod)},
        "udhaar": udh, "udhaarTotal": sum(u["balance"] for u in udh),
        "low": low, "products": prod,
    })

@app.post("/api/chat")
def api_chat():
    msg = (request.json or {}).get("message", "")
    try:
        reply = manager.handle_message("web", msg)
    except Exception as e:
        reply = f"Munshi ulajh gaya: {e}"
    return jsonify({"reply": reply})

@app.get("/health")
def health():
    return "ok"

@app.get("/api/dump")
def api_dump():
    """DB backup download (secret key se protected)."""
    if request.args.get("key") != os.environ.get("BACKUP_KEY", ""):
        return "unauthorized", 403
    from flask import send_file
    return send_file(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "db", "shop.db"),
                     as_attachment=True, download_name="shop.db")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
