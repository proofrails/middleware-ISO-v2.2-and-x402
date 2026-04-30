"""Demo landing page.

Only active when DEMO_MODE=true.
Serves a self-contained HTML page at GET /demo.
"""
from __future__ import annotations

from fastapi import APIRouter
from starlette.responses import HTMLResponse

router = APIRouter(tags=["demo"])

_DEMO_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>ProofRails — ISO 20022 Middleware Demo</title>
<style>
  *{margin:0;padding:0;box-sizing:border-box}
  body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#0a0e1a;color:#e2e8f0;min-height:100vh}
  a{color:#60a5fa;text-decoration:none}a:hover{text-decoration:underline}
  .container{max-width:960px;margin:0 auto;padding:2rem 1.5rem}
  .hero{text-align:center;padding:3rem 0 2rem}
  .hero h1{font-size:2.4rem;font-weight:700;background:linear-gradient(135deg,#60a5fa,#a78bfa);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:.5rem}
  .hero p{color:#94a3b8;font-size:1.1rem;max-width:600px;margin:0 auto 2rem}
  .badge{display:inline-block;background:#1e293b;border:1px solid #334155;border-radius:999px;padding:.35rem 1rem;font-size:.8rem;color:#94a3b8;margin-bottom:1.5rem}
  .btn{display:inline-block;padding:.75rem 2rem;border-radius:8px;font-size:1rem;font-weight:600;cursor:pointer;border:none;transition:all .15s}
  .btn-primary{background:linear-gradient(135deg,#3b82f6,#8b5cf6);color:#fff}.btn-primary:hover{opacity:.9;transform:translateY(-1px)}
  .btn-outline{background:transparent;border:1px solid #475569;color:#cbd5e1}.btn-outline:hover{border-color:#60a5fa;color:#60a5fa}
  .cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:1.5rem;margin:2rem 0}
  .card{background:#111827;border:1px solid #1f2937;border-radius:12px;padding:1.5rem}
  .card h3{font-size:1.1rem;margin-bottom:.75rem;color:#f1f5f9}
  .card p{color:#94a3b8;font-size:.9rem;line-height:1.5}
  table{width:100%;border-collapse:collapse;margin-top:1rem;font-size:.85rem}
  th{text-align:left;padding:.6rem .5rem;color:#64748b;border-bottom:1px solid #1f2937;font-weight:500}
  td{padding:.6rem .5rem;border-bottom:1px solid #1f2937}
  .status{display:inline-block;padding:.15rem .5rem;border-radius:999px;font-size:.75rem;font-weight:600}
  .status-anchored{background:#064e3b;color:#34d399}
  .status-pending{background:#713f12;color:#fbbf24}
  .status-awaiting_anchor{background:#1e3a5f;color:#60a5fa}
  .status-failed{background:#4c0519;color:#fb7185}
  .verify-box{display:flex;gap:.5rem;margin-top:.75rem}
  .verify-box input{flex:1;padding:.6rem .75rem;border-radius:8px;border:1px solid #334155;background:#0f172a;color:#e2e8f0;font-size:.85rem}
  .verify-box input:focus{outline:none;border-color:#60a5fa}
  #verify-result{margin-top:.75rem;padding:.75rem;border-radius:8px;font-size:.85rem;display:none}
  .links{display:flex;gap:1.5rem;justify-content:center;margin-top:2rem;flex-wrap:wrap}
  .spinner{display:none;width:18px;height:18px;border:2px solid #475569;border-top-color:#60a5fa;border-radius:50%;animation:spin .6s linear infinite;vertical-align:middle;margin-left:.5rem}
  @keyframes spin{to{transform:rotate(360deg)}}
  #try-spinner{display:none}
  .mono{font-family:'SF Mono',SFMono-Regular,Consolas,monospace;font-size:.8rem;word-break:break-all}
</style>
</head>
<body>
<div class="container">
  <div class="hero">
    <div class="badge">🔒 DEMO MODE — no wallet or API key needed</div>
    <h1>ProofRails</h1>
    <p>ISO 20022 compliance for blockchain payments. Record a transaction, watch it get bundled, signed, and anchored — all in seconds.</p>
    <button class="btn btn-primary" id="try-btn" onclick="tryIt()">
      ▶ Record a live transaction
      <span class="spinner" id="try-spinner"></span>
    </button>
  </div>

  <div class="cards">
    <div class="card">
      <h3>📋 Recent Transactions</h3>
      <p>Live data from the middleware pipeline.</p>
      <table>
        <thead><tr><th>Reference</th><th>Amount</th><th>Status</th></tr></thead>
        <tbody id="receipts-body"><tr><td colspan="3" style="color:#64748b">Loading...</td></tr></tbody>
      </table>
    </div>

    <div class="card">
      <h3>🔍 Verify a Bundle</h3>
      <p>Paste a bundle hash (0x...) to verify it against on-chain records.</p>
      <div class="verify-box">
        <input type="text" id="verify-input" placeholder="0x1234abcd..." />
        <button class="btn btn-outline" onclick="verifyBundle()">Verify</button>
      </div>
      <div id="verify-result"></div>
    </div>
  </div>

  <div class="links">
    <a href="/" class="btn btn-outline">📊 Full Dashboard</a>
    <a href="/docs" class="btn btn-outline">📖 API Docs (Swagger)</a>
    <a href="/v1/health" class="btn btn-outline">💚 Health Check</a>
  </div>
</div>

<script>
const BASE = '';

function statusClass(s) { return 'status status-' + (s || 'pending'); }

async function loadReceipts() {
  try {
    const r = await fetch(BASE + '/v1/receipts?page_size=8&scope=all');
    const data = await r.json();
    const tbody = document.getElementById('receipts-body');
    if (!data.items || data.items.length === 0) {
      tbody.innerHTML = '<tr><td colspan="3" style="color:#64748b">No receipts yet. Click the button above!</td></tr>';
      return;
    }
    tbody.innerHTML = data.items.map(it =>
      `<tr>
        <td><a href="/receipt/${it.id}" class="mono">${it.reference}</a></td>
        <td>${it.amount} ${it.currency}</td>
        <td><span class="${statusClass(it.status)}">${it.status}</span></td>
      </tr>`
    ).join('');
  } catch(e) {
    console.error('loadReceipts', e);
  }
}

async function tryIt() {
  const btn = document.getElementById('try-btn');
  const spinner = document.getElementById('try-spinner');
  btn.disabled = true;
  spinner.style.display = 'inline-block';
  try {
    const chains = ['flare','ethereum','base'];
    const chain = chains[Math.floor(Math.random()*chains.length)];
    const ccyMap = {flare:'FLR',ethereum:'ETH',base:'USDC'};
    const amt = (Math.random()*4990+10).toFixed(2);
    const now = Date.now();
    const hex = () => Math.random().toString(16).slice(2,10);
    const body = {
      tip_tx_hash: '0x' + hex() + hex() + hex() + hex() + hex() + hex() + hex() + hex(),
      chain: chain,
      amount: amt,
      currency: ccyMap[chain],
      sender_wallet: '0x' + hex() + hex() + hex() + hex() + hex(),
      receiver_wallet: '0x' + hex() + hex() + hex() + hex() + hex(),
      reference: 'demo:live:' + now + ':' + hex()
    };
    const r = await fetch(BASE + '/v1/iso/record-tip', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify(body)
    });
    const data = await r.json();
    if (data.receipt_id) {
      window.location.href = '/receipt/' + data.receipt_id;
    } else {
      alert('Error: ' + JSON.stringify(data));
    }
  } catch(e) {
    alert('Request failed: ' + e.message);
  } finally {
    btn.disabled = false;
    spinner.style.display = 'none';
  }
}

async function verifyBundle() {
  const input = document.getElementById('verify-input');
  const result = document.getElementById('verify-result');
  const hash = input.value.trim();
  if (!hash) return;
  result.style.display = 'block';
  result.style.background = '#1e293b';
  result.style.color = '#94a3b8';
  result.textContent = 'Verifying...';
  try {
    const r = await fetch(BASE + '/v1/iso/verify', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({bundle_hash: hash})
    });
    const data = await r.json();
    if (data.matches_onchain) {
      result.style.background = '#064e3b';
      result.style.color = '#34d399';
      result.innerHTML = '✅ <strong>Verified on-chain</strong><br/><span class="mono">TX: ' + (data.flare_txid||'N/A') + '</span>';
    } else {
      result.style.background = '#4c0519';
      result.style.color = '#fb7185';
      result.textContent = '❌ Not found on-chain' + (data.errors && data.errors.length ? ' — ' + data.errors.join(', ') : '');
    }
  } catch(e) {
    result.style.background = '#4c0519';
    result.style.color = '#fb7185';
    result.textContent = 'Error: ' + e.message;
  }
}

loadReceipts();
setInterval(loadReceipts, 10000);
</script>
</body>
</html>"""


@router.get("/demo", response_class=HTMLResponse)
def demo_landing():
    return HTMLResponse(content=_DEMO_HTML)
