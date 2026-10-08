"""A portable, read-only view of original problems, decisions and measured work."""

from __future__ import annotations

from html import escape
import json
import os
from pathlib import Path
from urllib.parse import quote

from .core import atomic_text
from .library import Library


REASONS = {"selected": "Selected within budget", "budget": "Waiting for budget",
           "no_execution_adapter": "Needs an evaluation adapter", "unconfirmed_intent": "Confirm original intent",
           "no_capability_match": "No matching capability claim", "needs_reharvest": "Source changed · harvest again",
           "already_attempted": "Already attempted · no duplicate call",
           "needs_rebuild_contract": "Needs independent rebuild brief and categorized checks"}


def e(value) -> str:
    return escape(str(value), quote=True)


def money(value) -> str:
    return "Unknown" if value is None else f"${value:.4f}"


def local_link(path: str, library: Library) -> str | None:
    resolved = Path(path).resolve()
    if not resolved.is_relative_to(library.path) or not resolved.is_file():
        return None
    return quote(os.path.relpath(resolved, library.path), safe="/")


def write_board(library: Library) -> Path:
    records = library.records()
    with library.transaction() as db:
        plans = [{**json.loads(row[0]), "status": row[1], "result": json.loads(row[2]) if row[2] else None}
                 for row in db.execute("SELECT body,status,result FROM plans ORDER BY rowid DESC")]
        events = [json.loads(row[0]) for row in db.execute("SELECT body FROM events ORDER BY rowid DESC LIMIT 12")]
        feeds = [dict(row) for row in db.execute("SELECT source,observed FROM catalogs ORDER BY source")]
    latest = plans[0] if plans else None
    decisions = {row["task_id"]: row for row in latest["decisions"]} if latest else {}
    campaigns = [p for p in plans if p["result"] is not None]
    tasks = [task for p in campaigns for task in p["result"]["tasks"]]
    known_cost = sum(p["result"]["known_spend_usd"] for p in campaigns)
    unknown = any(p["result"]["unknown"] for p in campaigns) or any(p["status"] == "running" for p in plans)
    measured = sum(bool(t["comparisons"]) for t in tasks)
    parked = sum(r["adapter"] is None for r in records)
    cards = []
    for record in records:
        decision = decisions.get(record["id"], {})
        reason = decision.get("reason", "no_execution_adapter" if not record["adapter"] else "awaiting_plan")
        state = "ready" if reason == "selected" else "parked" if not record["adapter"] else "saved"
        assumptions = record.get("assumptions", [])
        legacy = "".join(f"<li>{e(a.get('text', a))} <small>{e(a.get('source', 'Source not recorded'))}</small></li>"
                         if isinstance(a, dict) else f"<li>{e(a)} <small>Source not recorded</small></li>" for a in assumptions)
        failures = "".join(f"<li>{e(f)}</li>" for f in record["failures"])
        constraints = "".join(f"<li>{e(c)}</li>" for c in record["constraints"])
        cards.append(f'''<article class="task" data-state="{state}">
          <div class="task-top"><span class="tag">{e(record['kind'])}</span><span class="state {state}">{e(REASONS.get(reason, 'Saved · ready to plan'))}</span></div>
          <h3>{e(record['title'])}</h3><p class="intent">{e(record['intent']['text'])}</p>
          <div class="task-meta"><span>Impact <b>{e(record['revisit']['impact'])}/5</b></span><span>Declared cost <b>{money(record['revisit']['estimated_usd'])}</b></span></div>
          <p class="caps">{e(' · '.join(record['revisit']['capabilities']))}</p>
          <details><summary>Original problem &amp; provenance</summary>
          <p>Intent source: {e(record['intent']['source'])} · {'Confirmed' if record['intent']['confirmed'] else 'Unconfirmed'}</p>
          <h4>Observed failures</h4><ul>{failures or '<li>None recorded</li>'}</ul>
          <h4>Constraints</h4><ul>{constraints or '<li>None recorded</li>'}</ul>
          <h4>Legacy assumptions · not established facts</h4><ul>{legacy or '<li>None recorded</li>'}</ul>
          <p>Historical model: {e(record.get('capsule', {}).get('baseline', {}).get('model', 'unknown'))}</p>
          <p>Revision <code>{e(record['revision'][:12])}</code></p></details></article>''')
    queue_rows = "".join(f"<tr><td>{e(d['title'])}</td><td>{e(REASONS.get(d['reason'], d['reason']))}</td><td>{money(d['allocation_usd'])}</td></tr>"
                         for d in latest["decisions"]) if latest else ""
    queue = (f'''<div class="section-head"><h2>Next revisit queue</h2><span class="tag">{e(latest['status'])}</span></div>
        <p><b>{e(latest['candidate']['runtime_model'])}</b> · {e(latest['mode'])} · Trial {latest['trial']}
        · {money(latest['allocated_usd'])} allocated / {money(latest['budget_usd'])} stop budget</p>
        <p class="muted">{e(latest['method'])} Budgets are provider stops; in-flight calls may overshoot.</p>
        <div class="table-wrap"><table><thead><tr><th>Problem</th><th>Decision</th><th>Per-task stop</th></tr></thead><tbody>{queue_rows}</tbody></table></div>
        <details><summary>Candidate claim &amp; saved plan</summary><p>{e(latest['candidate']['evidence'])}</p>
        <code>secondlook revisit {e(latest['id'])} --library {e(str(library.path))}</code></details>'''
        if latest else '<h2>Next revisit queue</h2><p class="muted">Register a candidate and create a budgeted queue. No model calls are needed to plan.</p>')
    outcome_cards = []
    for plan in campaigns:
        campaign = plan["result"]
        for task in campaign["tasks"]:
            scores = []
            for arm, score in task["arms"].items():
                name = {"A": "Saved artifact", "B": "Ordinary", "C": "Intent first", "R": "Reference repair"}.get(arm, arm)
                scores.append(f"<div><small>{name}</small><strong>{e(score['passed']) if score['passed'] is not None else '—'}<span> / {e(score['total']) if score['total'] is not None else '—'}</span></strong></div>")
            outcomes = []
            for comparison, verdict in task["comparisons"].items():
                outcomes.append(f"<span class=tag>{e(comparison.replace('_', ' → '))}: {e(verdict['verdict'].replace('_', ' '))} · +{len(verdict['improvements'])} / −{len(verdict['regressions'])}</span>")
            link = local_link(task["report"], library)
            action = f'<a class="report-link" href="{e(link)}">Inspect screenshots, checks &amp; changes ↗</a>' if link else '<span>Detailed evidence unavailable</span>'
            sample = "SIMULATION · hand-authored repair, no model" if task["kind"] == "offline_reference" else "LIVE RUN · one sample per arm"
            tokens = f"{task['tokens']:,}" if task["tokens"] is not None else f"Unknown (known {task['known_tokens']:,})"
            models = sorted({model for key, score in task["arms"].items() if key != "A" for model in score["models"]})
            outcome_cards.append(f'''<article class="outcome"><div class="task-top"><span class="eyebrow">{sample}</span><span class="tag">{e(task['status'])}</span></div>
            <h3>{e(task['title'])}</h3><div class="scores">{''.join(scores)}</div><div class="verdicts">{''.join(outcomes)}</div>
            <p>Actual spend <b>{money(task['total_usd'])}</b> · Reported tokens <b>{e(tokens)}</b></p>
            <p class="muted">Resolved model: {e(', '.join(models) or 'No model call')}</p>{action}</article>''')
        if campaign["unknown"]:
            outcome_cards.append(f'<div class="alert">Campaign {e(plan["id"][:12])} needs reconciliation. Known spend {money(campaign["known_spend_usd"])}; total unknown. Further dispatch is blocked.</div>')
    changes = "".join(f"<li><span class=tag>{e(event['kind'])}</span> <b>{e(event['model_id'])}</b><small>{e(event['observed_at'])} · {e(event['source'])}</small></li>" for event in events)
    feed_text = "".join(f"<p class=muted>{e(feed['source'])} · checked {e(feed['observed'])}</p>" for feed in feeds)
    cost_text = f"≥ {money(known_cost)}" if unknown else money(known_cost)
    html = '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
    <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; img-src 'self' data:; base-uri 'none'; form-action 'none'">
    <title>Second Look · Problem library</title><style>
    :root{color-scheme:dark;--bg:#101615;--panel:#18211f;--edge:#34403b;--text:#edf1e9;--muted:#a8b7ab;--lime:#c9f279;--cyan:#96d8ce}
    *{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:15px/1.55 -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}
    main{max-width:1220px;margin:auto;padding:30px 32px 70px}nav{display:flex;justify-content:space-between;align-items:center;padding:0 0 38px;gap:12px}.brand{font-weight:760;font-size:22px;letter-spacing:-.8px}.brand i{color:var(--lime);font-style:normal;margin-right:10px}.local{color:var(--muted);font-size:12px;border:1px solid var(--edge);padding:5px 11px;border-radius:30px}
    .eyebrow{text-transform:uppercase;letter-spacing:1.5px;color:var(--cyan);font-size:11px;font-weight:700}h1{font-size:clamp(34px,5vw,57px);line-height:1.1;letter-spacing:-2px;max-width:770px;margin:16px 0}header>p{max-width:730px;color:var(--muted);font-size:17px}h2{font-size:23px;letter-spacing:-.7px;margin:0}h3{font-size:20px;letter-spacing:-.4px;margin:16px 0 8px}h4{margin:16px 0 5px;font-size:13px}.flow{display:flex;gap:12px;flex-wrap:wrap;margin:23px 0 30px;color:var(--muted);font-size:12px}.flow b{color:var(--lime)}
    .metrics{display:grid;grid-template-columns:repeat(4,1fr);border:1px solid var(--edge);border-radius:16px;overflow:hidden;margin:30px 0 42px}.metric{padding:21px 24px;background:var(--panel);border-right:1px solid var(--edge)}.metric:last-child{border:0}.metric strong{display:block;font-size:30px;letter-spacing:-1px}.metric small,.muted,small{color:var(--muted)}.section-head{display:flex;align-items:center;justify-content:space-between;gap:16px;margin-bottom:18px}section{margin:35px 0}.filters{display:flex;gap:5px;flex-wrap:wrap}button{font:inherit;font-size:12px;background:transparent;border:1px solid var(--edge);color:var(--muted);border-radius:25px;padding:6px 12px;cursor:pointer}button[aria-pressed=true]{background:var(--lime);color:#172013;border-color:var(--lime)}
    .cards{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}.task,.outcome,.queue,.observations{border:1px solid var(--edge);background:var(--panel);padding:23px;border-radius:15px;min-width:0}.task-top{display:flex;justify-content:space-between;gap:8px;align-items:start;flex-wrap:wrap}.tag{display:inline-block;border:1px solid var(--edge);border-radius:5px;padding:2px 7px;font-size:10px;color:var(--muted)}.state{font-size:10px;color:var(--muted)}.state.ready{color:var(--lime)}.state.parked{color:#e5c68c}.intent{color:#cbd4c9;font-size:14px;overflow-wrap:anywhere}.task-meta{display:flex;justify-content:space-between;gap:12px;font-size:11px;color:var(--muted);border-top:1px solid var(--edge);padding-top:15px;margin-top:20px}.task-meta b{color:var(--text)}.caps{font-size:11px;color:var(--cyan)}details{border-top:1px solid var(--edge);margin-top:18px;padding-top:13px;font-size:12px;color:var(--muted)}summary{cursor:pointer;color:var(--text)}details li{margin:6px 0}details small,.observations small{display:block}code{overflow-wrap:anywhere;font-size:11px}.table-wrap{overflow:auto}table{width:100%;border-collapse:collapse;font-size:13px}th{text-align:left;font-size:10px;text-transform:uppercase;color:var(--muted);letter-spacing:1px}td,th{padding:14px 8px;border-bottom:1px solid var(--edge)}td:first-child{font-weight:600}td:last-child{text-align:right;white-space:nowrap}
    .outcomes{display:grid;gap:16px}.scores{display:flex;gap:35px;margin:23px 0}.scores small{display:block;font-size:11px}.scores strong{display:block;font-size:32px;letter-spacing:-1px;color:var(--lime)}.scores strong span{font-size:17px;color:var(--muted)}.verdicts{display:flex;gap:8px;flex-wrap:wrap}.report-link{display:inline-block;color:var(--lime);text-decoration:none;border-bottom:1px solid #82995b;padding-bottom:3px;font-size:13px}.alert{border:1px solid #ad8652;background:#302819;padding:18px;border-radius:10px}.observations ul{padding:0;list-style:none}.observations li{border-top:1px solid var(--edge);padding:12px 0}.observations p,.observations li{overflow-wrap:anywhere}footer{border-top:1px solid var(--edge);padding-top:24px;color:var(--muted);font-size:12px}button:focus-visible,summary:focus-visible,a:focus-visible{outline:2px solid var(--lime);outline-offset:4px}[hidden]{display:none!important}
    @media(max-width:900px){.cards{grid-template-columns:1fr 1fr}.metrics{grid-template-columns:1fr 1fr}.metric:nth-child(2){border-right:0}.metric:nth-child(-n+2){border-bottom:1px solid var(--edge)}}@media(max-width:600px){main{padding:20px 17px 45px}nav{padding-bottom:24px}.cards{grid-template-columns:1fr}.section-head{align-items:start;flex-direction:column}.metric{padding:16px}.metric strong{font-size:25px}.task,.queue,.outcome,.observations{padding:18px}.scores{gap:23px}h1{letter-spacing:-1.5px}.local{font-size:10px}}
    </style></head><body><main>'''
    html += f'''<nav><div class="brand"><i>◉</i>Second Look</div><span class="local">LOCAL LIBRARY · NO AUTOMATIC SPEND</span></nav>
    <header><span class="eyebrow">Harvest now. Solve when it matters.</span><h1>Your old problems.<br>A fresh chance to solve them.</h1>
    <p>Keep the original goal. Notice model changes. Revisit only what fits your budget—and inspect what actually improved.</p>
    <div class="flow"><span><b>01</b> Preserve intent</span><span>→</span><span><b>02</b> Observe changes</span><span>→</span><span><b>03</b> Select &amp; revisit</span><span>→</span><span><b>04</b> Compare evidence</span></div></header>
    <div class="metrics"><div class="metric"><strong>{len(records)}</strong><small>Problems preserved</small></div><div class="metric"><strong>{measured}</strong><small>Revisits with comparisons</small></div><div class="metric"><strong>{parked}</strong><small>Awaiting an adapter</small></div><div class="metric"><strong>{cost_text}</strong><small>{'Known spend · total unknown' if unknown else 'Recorded API-equivalent spend'}</small></div></div>
    <section><div class="section-head"><h2>Problem library</h2><div class="filters" role="group" aria-label="Filter problems"><button data-filter="all" aria-pressed="true">All problems</button><button data-filter="ready" aria-pressed="false">Selected</button><button data-filter="parked" aria-pressed="false">Parked</button></div></div><div class="cards">{''.join(cards) or '<p>No problems harvested yet.</p>'}</div></section>
    <section class="queue">{queue}</section><section><div class="section-head"><h2>What actually changed</h2><span class="muted">Frozen checks · actual receipts</span></div><div class="outcomes">{''.join(outcome_cards) or '<p class="muted">No measured revisits yet. A model announcement is a reason to investigate, not evidence of improvement.</p>'}</div></section>
    <section class="observations"><h2>Model observations</h2><p class="muted">The first sync creates an inventory. Later changes are catalog observations; they do not establish better task performance.</p>{feed_text}<ul>{changes or '<li>No catalog changes observed.</li>'}</ul></section>
    <footer>Static HTML execution adapter · Other problem types can be preserved for future adapters.<br>Pass counts describe the saved checks. Screenshot changes are not quality scores. Historical model identity stays unknown unless documented.</footer>
    <script>document.querySelectorAll('[data-filter]').forEach(b=>b.addEventListener('click',()=>{{document.querySelectorAll('[data-filter]').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));document.querySelectorAll('.task').forEach(x=>x.hidden=b.dataset.filter!=='all'&&x.dataset.state!==b.dataset.filter);}}));</script></main></body></html>'''
    output = library.path / "board.html"
    atomic_text(output, html)
    return output
