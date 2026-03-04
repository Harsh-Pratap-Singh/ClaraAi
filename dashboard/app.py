"""
Clara AI Pipeline – Web Dashboard
A simple Flask-based dashboard for viewing pipeline outputs, diffs, and status.
"""
from __future__ import annotations
import json, os, sys
from pathlib import Path
from flask import Flask, render_template_string, jsonify, request

# Add parent to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.config import OUTPUT_DIR, ACCOUNTS_DIR
from scripts.storage import list_accounts, load_json, get_run_summary

app = Flask(__name__)

# ── HTML Template ─────────────────────────────────────────────────────
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Clara AI Pipeline Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f172a; color: #e2e8f0; }
        .container { max-width: 1200px; margin: 0 auto; padding: 2rem; }
        h1 { font-size: 2rem; margin-bottom: 0.5rem; color: #38bdf8; }
        .subtitle { color: #94a3b8; margin-bottom: 2rem; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 2rem; }
        .stat-card { background: #1e293b; border-radius: 12px; padding: 1.5rem; border: 1px solid #334155; }
        .stat-value { font-size: 2rem; font-weight: 700; color: #38bdf8; }
        .stat-label { color: #94a3b8; font-size: 0.875rem; margin-top: 0.25rem; }
        .accounts { display: grid; gap: 1rem; }
        .account-card { background: #1e293b; border-radius: 12px; padding: 1.5rem; border: 1px solid #334155; cursor: pointer; transition: all 0.2s; }
        .account-card:hover { border-color: #38bdf8; transform: translateY(-2px); }
        .account-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; }
        .company-name { font-size: 1.25rem; font-weight: 600; color: #f1f5f9; }
        .version-badges { display: flex; gap: 0.5rem; }
        .badge { padding: 0.25rem 0.75rem; border-radius: 9999px; font-size: 0.75rem; font-weight: 600; }
        .badge-v1 { background: #164e63; color: #67e8f9; }
        .badge-v2 { background: #14532d; color: #86efac; }
        .badge-missing { background: #451a03; color: #fbbf24; }
        .account-id { color: #64748b; font-size: 0.875rem; font-family: monospace; }
        .detail-panel { display: none; margin-top: 1rem; }
        .detail-panel.active { display: block; }
        .tabs { display: flex; gap: 0.5rem; margin-bottom: 1rem; flex-wrap: wrap; }
        .tab { padding: 0.5rem 1rem; border-radius: 8px; background: #334155; color: #94a3b8; cursor: pointer; border: none; font-size: 0.875rem; }
        .tab.active { background: #38bdf8; color: #0f172a; }
        .code-block { background: #0f172a; border: 1px solid #334155; border-radius: 8px; padding: 1rem; overflow-x: auto; font-family: 'Fira Code', 'Cascadia Code', monospace; font-size: 0.8rem; line-height: 1.5; max-height: 500px; overflow-y: auto; white-space: pre-wrap; }
        .diff-added { color: #86efac; background: rgba(34, 197, 94, 0.1); }
        .diff-removed { color: #fca5a5; background: rgba(239, 68, 68, 0.1); text-decoration: line-through; }
        .diff-section { margin-bottom: 1rem; }
        .diff-header { font-weight: 600; color: #38bdf8; margin-bottom: 0.5rem; }
        .changelog-content { background: #0f172a; border: 1px solid #334155; border-radius: 8px; padding: 1.5rem; line-height: 1.8; }
        .changelog-content h1, .changelog-content h2, .changelog-content h3 { color: #38bdf8; margin-top: 1rem; margin-bottom: 0.5rem; }
        .loading { text-align: center; padding: 2rem; color: #64748b; }
        .error { color: #fca5a5; padding: 1rem; background: rgba(239, 68, 68, 0.1); border-radius: 8px; }
        a { color: #38bdf8; text-decoration: none; }
        a:hover { text-decoration: underline; }
        .refresh-btn { background: #38bdf8; color: #0f172a; border: none; padding: 0.5rem 1rem; border-radius: 8px; cursor: pointer; font-weight: 600; margin-bottom: 1rem; }
        .refresh-btn:hover { background: #7dd3fc; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 Clara AI Pipeline</h1>
        <p class="subtitle">Demo Call → Retell Agent Draft → Onboarding Updates → Agent Revision</p>
        
        <button class="refresh-btn" onclick="loadData()">↻ Refresh</button>
        
        <div class="stats" id="stats">
            <div class="stat-card"><div class="stat-value" id="total-accounts">-</div><div class="stat-label">Total Accounts</div></div>
            <div class="stat-card"><div class="stat-value" id="v1-count">-</div><div class="stat-label">v1 (Demo Processed)</div></div>
            <div class="stat-card"><div class="stat-value" id="v2-count">-</div><div class="stat-label">v2 (Onboarding Updated)</div></div>
        </div>
        
        <h2 style="margin-bottom: 1rem; color: #f1f5f9;">Accounts</h2>
        <div class="accounts" id="accounts-list">
            <div class="loading">Loading accounts...</div>
        </div>
    </div>

    <script>
        let accountsData = {};

        async function loadData() {
            try {
                const resp = await fetch('/api/summary');
                const data = await resp.json();
                
                document.getElementById('total-accounts').textContent = data.total_accounts;
                document.getElementById('v1-count').textContent = data.accounts.filter(a => a.has_v1).length;
                document.getElementById('v2-count').textContent = data.accounts.filter(a => a.has_v2).length;
                
                const list = document.getElementById('accounts-list');
                list.innerHTML = '';
                
                for (const account of data.accounts) {
                    const card = document.createElement('div');
                    card.className = 'account-card';
                    card.innerHTML = `
                        <div class="account-header">
                            <span class="company-name">${account.company_name}</span>
                            <div class="version-badges">
                                ${account.has_v1 ? '<span class="badge badge-v1">v1</span>' : '<span class="badge badge-missing">No v1</span>'}
                                ${account.has_v2 ? '<span class="badge badge-v2">v2</span>' : ''}
                            </div>
                        </div>
                        <div class="account-id">${account.account_id}</div>
                        <div class="detail-panel" id="detail-${account.account_id}">
                            <div class="tabs" id="tabs-${account.account_id}"></div>
                            <div class="code-block" id="content-${account.account_id}">Select a tab to view details</div>
                        </div>
                    `;
                    card.onclick = () => toggleDetail(account.account_id, account.has_v1, account.has_v2);
                    list.appendChild(card);
                }
            } catch (e) {
                document.getElementById('accounts-list').innerHTML = '<div class="error">Failed to load data: ' + e.message + '</div>';
            }
        }

        async function toggleDetail(accountId, hasV1, hasV2) {
            const panel = document.getElementById('detail-' + accountId);
            if (panel.classList.contains('active')) {
                panel.classList.remove('active');
                return;
            }
            panel.classList.add('active');
            
            const tabsEl = document.getElementById('tabs-' + accountId);
            const tabs = [];
            if (hasV1) tabs.push('v1-memo', 'v1-agent');
            if (hasV2) tabs.push('v2-memo', 'v2-agent', 'changelog', 'diff');
            
            tabsEl.innerHTML = tabs.map((t, i) => 
                `<button class="tab ${i === 0 ? 'active' : ''}" onclick="event.stopPropagation(); loadTab('${accountId}', '${t}', this)">${t}</button>`
            ).join('');
            
            if (tabs.length > 0) loadTab(accountId, tabs[0]);
        }

        async function loadTab(accountId, tab, btnEl) {
            const contentEl = document.getElementById('content-' + accountId);
            contentEl.textContent = 'Loading...';
            
            // Update active tab styling
            if (btnEl) {
                btnEl.parentElement.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                btnEl.classList.add('active');
            }
            
            try {
                const resp = await fetch(`/api/account/${accountId}/${tab}`);
                const data = await resp.json();
                
                if (tab === 'changelog') {
                    contentEl.innerHTML = '<div class="changelog-content">' + (data.content || 'No changelog available') + '</div>';
                } else if (tab === 'diff') {
                    renderDiff(contentEl, data);
                } else {
                    contentEl.textContent = JSON.stringify(data.content, null, 2);
                }
            } catch (e) {
                contentEl.textContent = 'Error loading: ' + e.message;
            }
        }

        function renderDiff(el, data) {
            if (!data.content || (!data.content.changed && !data.content.added && !data.content.removed)) {
                el.textContent = 'No diff available';
                return;
            }
            let html = '';
            const c = data.content;
            if (c.changed && Object.keys(c.changed).length) {
                html += '<div class="diff-section"><div class="diff-header">Changed</div>';
                for (const [path, vals] of Object.entries(c.changed)) {
                    html += `<div><strong>${path}</strong></div>`;
                    html += `<div class="diff-removed">- ${JSON.stringify(vals.old)}</div>`;
                    html += `<div class="diff-added">+ ${JSON.stringify(vals.new)}</div><br>`;
                }
                html += '</div>';
            }
            if (c.added && Object.keys(c.added).length) {
                html += '<div class="diff-section"><div class="diff-header">Added</div>';
                for (const [path, val] of Object.entries(c.added)) {
                    html += `<div class="diff-added">+ ${path}: ${JSON.stringify(val)}</div>`;
                }
                html += '</div>';
            }
            if (c.removed && Object.keys(c.removed).length) {
                html += '<div class="diff-section"><div class="diff-header">Removed</div>';
                for (const [path, val] of Object.entries(c.removed)) {
                    html += `<div class="diff-removed">- ${path}: ${JSON.stringify(val)}</div>`;
                }
                html += '</div>';
            }
            el.innerHTML = html || 'No differences detected';
        }

        loadData();
    </script>
</body>
</html>
"""


# ── Routes ────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template_string(DASHBOARD_HTML)


@app.route("/api/summary")
def api_summary():
    return jsonify(get_run_summary())


@app.route("/api/account/<account_id>/<tab>")
def api_account_tab(account_id, tab):
    base = ACCOUNTS_DIR / account_id
    
    file_map = {
        "v1-memo": base / "v1" / "account_memo.json",
        "v1-agent": base / "v1" / "agent_spec.json",
        "v2-memo": base / "v2" / "account_memo.json",
        "v2-agent": base / "v2" / "agent_spec.json",
        "changelog": base / "v2" / "changelog.md",
        "diff": base / "v2" / "changes.json",
    }
    
    path = file_map.get(tab)
    if not path or not path.exists():
        return jsonify({"content": None, "error": "Not found"}), 404
    
    text = path.read_text(encoding="utf-8")
    
    if tab == "changelog":
        # Convert markdown to basic HTML
        import re
        html = text
        html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
        html = re.sub(r'^\- \*\*(.+?)\*\*(.*)$', r'<div>• <strong>\1</strong>\2</div>', html, flags=re.MULTILINE)
        html = re.sub(r'^\*\*(.+?)\*\*(.*)$', r'<div><strong>\1</strong>\2</div>', html, flags=re.MULTILINE)
        html = re.sub(r'^---$', r'<hr>', html, flags=re.MULTILINE)
        html = re.sub(r'`([^`]+)`', r'<code style="background:#334155;padding:2px 6px;border-radius:4px">\1</code>', html)
        return jsonify({"content": html})
    else:
        return jsonify({"content": json.loads(text)})


@app.route("/api/tasks")
def api_tasks():
    tracker = OUTPUT_DIR / "task_tracker.json"
    if tracker.exists():
        return jsonify(json.loads(tracker.read_text(encoding="utf-8")))
    return jsonify([])


# ── Main ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 50)
    print("  Clara AI Pipeline Dashboard")
    print("  http://localhost:8080")
    print("=" * 50)
    app.run(host="0.0.0.0", port=8080, debug=True)
