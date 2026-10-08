"""Portable HTML evidence report. All artifact/model text is escaped."""

from __future__ import annotations

import base64
from html import escape
import json
from pathlib import Path

from .core import atomic_text
from .evaluate import category_scores


def esc(value: object) -> str:
    return escape(str(value), quote=True)


def usd(value) -> str:
    return "Unknown" if value is None else f"${value:.4f}"


def check_state(row: dict | None) -> str:
    if not row or row.get("error_kind") == "harness":
        return "unknown"
    return "pass" if row["passed"] else "fail"


def write_report(result: dict, output: Path) -> Path:
    output = Path(output)
    arms = result.get("arms", {})
    checks = result.get("capsule", {}).get("checks", [])
    cost = result.get("cost", {})
    offline = result.get("kind") == "offline_reference"
    probe_only = result.get("kind") == "baseline_probe"
    imported = result.get("kind") == "imported_candidates"
    intent = result.get("capsule", {}).get("intent", {})
    candidates = [key for key in arms if key != "A"]
    candidate = candidates[0] if len(candidates) == 1 else None
    delta = result.get("comparisons", {}).get(f"A_{candidate}", {})
    workflow = result.get("comparisons", {}).get("B_C", {})
    verdicts = {"improved": "Measured improvement", "regression": "Regression detected",
                "no_measured_gain": "No measured gain", "inconclusive": "Inconclusive"}
    headline = verdicts.get(delta.get("verdict"), "No candidate measured")
    if len(candidates) > 1:
        candidate_deltas = [result.get("comparisons", {}).get(f"A_{key}", {}) for key in candidates]
        headline = ("Regression detected in at least one workflow" if any(d.get("verdict") == "regression" for d in candidate_deltas)
                    else f"{len(candidates)} revision workflows measured")
    if result.get("status") == "skipped_baseline_passes":
        headline = "Checks already pass. Budget saved."
    elif result.get("status") == "probe_completed":
        headline = "Baseline checked. No model budget spent."
    elif result.get("status") != "completed":
        headline = "Inconclusive run"
    gains, losses = len(delta.get("improvements", [])), len(delta.get("regressions", []))
    delta_html = (f'<strong>{len(candidates)}</strong><span>candidate workflows</span><b>Inspect every comparison</b>'
                  if len(candidates) > 1 else f'<strong>+{gains}</strong><span>new passes</span><b>{losses} regressions</b>')
    workflow_note = ("No model was called. This compares a deliberately flawed synthetic app with a hand-authored reference repair."
                     if offline else "A → candidate measures changes to this artifact, not pure model uplift.")
    if probe_only:
        workflow_note = "No model was called. Failed checks identify behavior worth investigating; intent confirmation is unchanged."
    if imported:
        workflow_note = ("Imported outputs, evaluated locally. Model labels and generation usage are owner-reported and unverified. "
                         "Zero local model calls does not mean external generation was free. This measures artifact behavior, not model superiority.")
        headline = headline.replace("revision workflows", "imported candidates").replace("workflow", "candidate")
    if workflow:
        workflow_note += " " + ("Reframing added no measured functional gain over ordinary improvement." if workflow.get("verdict") == "no_measured_gain"
                                  else "Workflow comparison B → C: " + verdicts.get(workflow.get("verdict"), "Inconclusive") + ".")
    if "D" in arms:
        workflow_note += " D builds from the independent brief and declared read-only inputs, with no legacy writable source. C uses two calls; B and D use one. Equal caps do not imply equal actual spend."
    comparison_rows = []
    for key, comparison in result.get("comparisons", {}).items():
        reason = f'<small class="time">{esc(comparison["reason"])}</small>' if comparison.get("reason") else ""
        comparison_rows.append(f'<tr><th scope="row">{esc(key.replace("_", " → "))}</th><td>{esc(verdicts.get(comparison.get("verdict"), "Inconclusive"))}{reason}</td><td>{len(comparison.get("improvements", []))}</td><td>{len(comparison.get("regressions", []))}</td></tr>')
    comparison_panel = ('<section class="section"><h2>Every comparison</h2><div class="table-wrap"><table aria-label="Pairwise comparisons"><thead><tr><th>Versions</th><th>Measured result</th><th>New passes</th><th>Regressions</th></tr></thead><tbody>'
                        + "".join(comparison_rows) + '</tbody></table></div><p class="caption">Each row reads left → right. Any lost pass takes precedence over new passes. One sample per workflow; there is no automatic winner or adoption.</p></section>') if comparison_rows else ""
    cards = []
    for name, arm in arms.items():
        evaluation = arm.get("evaluation", {})
        passed, total = evaluation.get("passed"), evaluation.get("total", len(checks))
        ratio = "—" if passed is None else f"{passed}<span>/{total}</span>"
        bar_class = {"pass": "ok", "fail": "bad", "unknown": "unknown"}
        bars = "".join(f'<i class="{bar_class[check_state(row)]}" title="{esc(row["id"])}"></i>' for row in evaluation.get("checks", []))
        model = ", ".join(arm.get("models", [])) or "Model unverified"
        if imported and arm.get("declared_model"):
            model = "Owner-reported label (unverified): " + arm["declared_model"]
        tokens = arm.get("tokens", {}).get("total")
        token_label = "unreported" if tokens is None else f"{tokens:,}"
        error = f'<p class="error">{esc(arm["error"])}</p>' if arm.get("error") else ""
        category_text = "".join(f'<p class="category-score">{esc(category.title())}: {score["passed"]}/{score["total"]}'
                                + (f' · {score["unmeasured"]} unmeasured' if score["unmeasured"] else '') + '</p>'
                                for category, score in category_scores(checks, evaluation).items() if category != "uncategorized")
        cap_text = f'<p class="caption">Effective cap {usd(arm["budget_usd"])}</p>' if "budget_usd" in arm else ""
        if arm.get("evaluation_reused_from"):
            cap_text += f'<p class="caption">Reused browser evidence from {esc(arm["evaluation_reused_from"])}: identical source. This is not another independent sample.</p>'
        cards.append(f'''<article class="arm"><div class="arm-top"><span class="letter">{esc(name)}</span><span class="state">{esc(arm.get('status','unknown'))}</span></div>
<h3>{esc(arm.get('label', name))}</h3><div class="score">{ratio}<small>checks passed</small></div><div class="bars">{bars}</div>
{category_text}<div class="arm-foot"><span>{usd(arm.get('cost_usd'))}</span><span>{token_label} tokens</span></div><p class="model">{esc(model)}</p>{cap_text}{error}</article>''')
    rows = []
    for check in checks:
        cells, outcomes = [], []
        for arm in arms.values():
            row = next((r for r in arm.get("evaluation", {}).get("checks", []) if r["id"] == check["id"]), None)
            state = check_state(row)
            outcomes.append(state)
            title = (row.get("error") if row else None) or {
                "pass": "Checked successfully", "fail": "Check failed; detailed evidence is in the original run",
                "unknown": "Not measured or evaluation could not complete",
            }[state]
            timing = f'{row["duration_ms"]:.0f} ms' if row and "duration_ms" in row else ""
            cells.append(f'<td><span class="badge {state}" title="{esc(title)}">{state.upper()}</span><small class="time">{timing}</small></td>')
        held_out = '<span class="holdout">HOLDOUT</span>' if check.get("held_out") else ""
        category = (f'<span class="holdout" title="{esc(check.get("basis", ""))}">{esc(check["category"].upper())}</span>'
                    if "category" in check else "")
        changed = str(len(set(outcomes)) > 1).lower()
        rows.append(f'<tr data-changed="{changed}" data-holdout="{str(bool(check.get("held_out"))).lower()}"><th scope="row">{esc(check.get("name",check["id"]))}{category}{held_out}</th>{"".join(cells)}</tr>')
    screenshots = []
    shot_states = sorted(set(key for arm in arms.values() for key in arm.get("evaluation", {}).get("screenshots", {})), key=lambda k: (k == "initial", k))
    for state in shot_states:
        figures = []
        for name, arm in arms.items():
            path = arm.get("evaluation", {}).get("screenshots", {}).get(state)
            if path and Path(path).is_file():
                encoded = base64.b64encode(Path(path).read_bytes()).decode()
                figures.append(f'<figure><figcaption><span class="letter small">{esc(name)}</span>{esc(arm.get("label",name))}</figcaption><button class="zoom" aria-label="Enlarge {esc(name)} screenshot"><img alt="{esc(name)}: {esc(state)} state" loading="lazy" src="data:image/png;base64,{encoded}"></button></figure>')
        hidden = " hidden" if state != shot_states[0] else ""
        screenshots.append(f'<div class="shots" data-shot="{esc(state)}"{hidden}>{"".join(figures)}</div>')
    details = []
    for name, arm in arms.items():
        if arm.get("diff"):
            details.append(f'<details><summary>{esc(name)} · Source diff <span>{esc(arm.get("summary",""))}</span></summary><p class="caption">{esc(arm.get("diff_note", "Unified source diff"))}</p><pre>{esc(arm["diff"])}</pre></details>')
        if arm.get("brief"):
            details.append(f'<details><summary>{esc(name)} · Intent brief, written before seeing the code</summary><pre>{esc(json.dumps(arm["brief"], ensure_ascii=False, indent=2))}</pre></details>')
    token_totals = [arm.get("tokens", {}).get("total") for arm in arms.values()]
    total_tokens = f"{sum(token_totals):,}" if all(value is not None for value in token_totals) else "Unknown"
    budget_used = 0 if not cost.get("limit_usd") or cost.get("known_spend_usd") is None else min(100, 100 * cost["known_spend_usd"] / cost["limit_usd"])
    evidence = {"status": result.get("status"), "manifest": result.get("manifest", {}), "fingerprint": result.get("fingerprint"),
                "source_unchanged": result.get("source_unchanged"), "source_context": result.get("source_context"),
                "model_calls": result.get("model_calls"), "cost": cost, "comparisons": result.get("comparisons", {})}
    selection = result.get("source_context", {})
    context_panel = ""
    if selection:
        context_panel = f'''<section class="context-budget"><span class="eyebrow">SELECTED SOURCE CONTEXT</span>
<div class="context-values"><div><strong>{selection['runtime_bytes']:,}</strong><span>bytes in local runtime</span></div>
<span class="context-arrow">→</span><div><strong>{selection['context_bytes']:,}</strong><span>bytes of selected source context</span></div></div>
<p class="caption">{selection['excluded_bytes']:,} UTF-8 source bytes excluded from context, not measured token savings. Prompt overhead is additional. Full source runs locally; protected regions stay unchanged.</p></section>'''
    provenance = '<p class="caption">' + esc(intent.get("source", "Source not recorded")) + ' · Intent confirmed: ' + esc(intent.get("confirmed", "unrecorded")) + '</p>'
    if intent.get("provenance"):
        provenance += '<pre>' + esc(json.dumps(intent["provenance"], ensure_ascii=False, indent=2)) + '</pre>'
    if result.get("capsule", {}).get("rebuild"):
        provenance += '<h3>Independent requirements</h3><pre>' + esc(json.dumps(result["capsule"]["rebuild"], ensure_ascii=False, indent=2)) + '</pre>'
    frozen = result.get("manifest", {})
    frozen_note = (f'<p class="caption">Checks frozen at {esc(frozen.get("checks_frozen_at", "unrecorded"))} · SHA-256 {esc(frozen.get("checks", "unrecorded"))}. Category provenance is available on each label and in the frozen capsule.</p>'
                   if any("category" in check for check in checks) else "")
    shared = result.get("sharing")
    evidence_links = ('<p class="caption"><a href="summary.json">Exported summary JSON</a> · ' + esc(shared["note"]) + '</p>' if shared else
                      '<p class="caption"><a href="result.json">Full result JSON</a> · <a href="capsule.frozen.json">Frozen capsule</a> · Raw call receipts and prompts are in the receipts folder.</p>')
    inspection_title = "Evidence included in this export." if shared else "Nothing hidden behind a score."
    if imported and not shared:
        evidence_links = '<p class="caption"><a href="result.json">Full result JSON</a> · <a href="capsule.frozen.json">Frozen capsule</a> · Imported responses are in the responses folder; they are not provider receipts.</p>'
    cost_detail = "External generation cost" if imported else "Experiment cost"
    cost_limit = "" if imported else f' <small>/ {usd(cost.get("limit_usd"))} stop budget</small>'
    cost_note = "" if imported else ". Failed calls count. Provider stops can overshoot by one in-flight response."
    checks_note = ("Check definitions are omitted from the exported request. External generation context and timing are unverified. "
                   if imported else "Check definitions are not sent to the model. ")
    html = '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src data:; style-src 'unsafe-inline'; script-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>Second Look · Revisit report</title><style>''' + CSS + '''</style></head><body><main>
<header><a class="brand" href="#">◉ SECOND LOOK<span>REVISIT / 006</span></a><span class="status-label">''' + ("IMPORTED CANDIDATES" if imported else "BASELINE PROBE" if probe_only else "OFFLINE REFERENCE" if offline else "LIVE MODEL EXPERIMENT") + '''</span></header>
<section class="hero"><div class="eyebrow">NEW MODEL. OLD WORK. FRESH EVIDENCE.</div><h1>See what actually<br>got better<span class="dot">.</span></h1><p class="project">''' + esc(result.get("capsule", {}).get("title", "Revisit")) + '''</p><p class="caption">Source: ''' + esc(result.get("capsule", {}).get("baseline", {}).get("provenance", "Provenance not recorded")) + '''</p></section>
<section class="verdict"><div><span class="eyebrow">THE RESULT</span><h2>''' + esc(headline) + '''</h2><p>''' + esc(workflow_note) + '''</p></div><div class="delta">''' + delta_html + '''</div></section>
<section class="arms">''' + "".join(cards) + '''</section>''' + comparison_panel + '''
<section class="budget"><div><span class="eyebrow">''' + cost_detail.upper() + '''</span><h3>''' + usd(cost.get("total_usd")) + cost_limit + '''</h3><div class="meter"><i style="width:''' + str(budget_used) + '''%"></i></div></div><div><strong>''' + total_tokens + '''</strong><span>reported tokens, including cache reads/writes</span></div><p>''' + esc(cost.get("basis", "Cost basis unavailable") + cost_note) + '''</p></section>
''' + context_panel + '''<details class="intent"><summary>Original intent <span>Preserved before the revision</span></summary><p>''' + esc(intent.get("text", "Unrecorded")) + '''</p>''' + provenance + '''</details>
<section class="section"><div class="section-heading"><div><span class="eyebrow">01 / BEHAVIOR</span><h2>The same checks. Every version.</h2></div><div class="filters" role="group" aria-label="Filter checks"><button class="active" data-filter="all" aria-pressed="true">All</button><button data-filter="changed" aria-pressed="false">Changed</button><button data-filter="holdout" aria-pressed="false">Holdout</button></div></div>
<div class="table-wrap"><table><thead><tr><th>Frozen acceptance check</th>''' + "".join(f"<th>{esc(k)}</th>" for k in arms) + '''</tr></thead><tbody>''' + "".join(rows) + '''</tbody></table></div>''' + frozen_note + '''<p class="caption">''' + checks_note + '''Holdout cases require inputs unavailable in shared source/data; ordinary visible inputs are not holdouts. Timings include navigation, actions and assertion waits; these are not performance benchmarks. Hover a result for failure details.</p></section>
<section class="section"><div class="section-heading"><div><span class="eyebrow">02 / VISIBLE CHANGE</span><h2>Look at the same moment.</h2></div><label class="select-label">Screen state <select id="shot-state">''' + "".join(f'<option value="{esc(state)}">{esc(state)}</option>' for state in shot_states) + '''</select></label></div>''' + ("".join(screenshots) or '<p class="caption">No screenshots captured.</p>') + '''<p class="caption">Same viewport for each corresponding check; 1200 × 820 by default. Per-check dimensions are in the evidence JSON. Click any image to inspect it. Visual differences are evidence, not an automatic quality score.</p></section>
<section class="section"><span class="eyebrow">03 / INSPECT THE WORK</span><h2>''' + inspection_title + '''</h2>''' + "".join(details) + '''<details><summary>Run identity, costs and comparison evidence</summary><pre>''' + esc(json.dumps(evidence, ensure_ascii=False, indent=2)) + '''</pre></details>''' + evidence_links + '''</section>
<footer><strong>Second Look</strong><p>One task. One sample per arm. Evidence of checked behavior, not proof of general model superiority.<br>Original artifacts are preserved. Review the patch before adopting a change.</p><span>''' + esc(result.get("created_at", "")) + '''</span></footer>
</main><dialog id="lightbox"><button id="close-dialog" aria-label="Close image">Close ×</button><img alt="Enlarged comparison screenshot"></dialog><script>''' + SCRIPT + '''</script></body></html>'''
    path = output / "report.html"
    atomic_text(path, html)
    return path


CSS = """
.caption{overflow-wrap:anywhere}.category-score{font-size:12px;margin:6px 0;color:var(--muted)}
.context-budget{margin-top:16px;padding:20px 24px;border:1px solid var(--line);border-radius:5px}.context-values{display:flex;align-items:center;gap:22px;flex-wrap:wrap;margin-top:8px}.context-values>div{display:flex;flex-direction:column}.context-values strong{font-size:23px;letter-spacing:-.6px}.context-values span{font-size:11px;color:var(--muted)}.context-arrow{font-size:24px!important}
:root{color-scheme:light;font:15px/1.6 -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#25302b;background:#f6f5ef;--line:#dcded4;--green:#20684a;--muted:#70786e}*{box-sizing:border-box}body{margin:0}main{max-width:1220px;padding:0 40px;margin:auto}header{display:flex;justify-content:space-between;align-items:center;gap:18px;padding:28px 0;border-bottom:1px solid var(--line)}a{color:inherit}.brand{display:flex;align-items:center;gap:24px;text-decoration:none;font-weight:850;font-size:16px;letter-spacing:.06em}.brand span{font-weight:500;font-size:11px;letter-spacing:.12em;color:var(--muted)}.status-label{font-size:10px;border:1px solid #c3ccbc;border-radius:20px;padding:5px 10px;letter-spacing:.08em;white-space:nowrap}.hero{padding:56px 0 32px}.eyebrow{font-size:10px;font-weight:750;letter-spacing:.13em;color:var(--muted)}h1{font-family:Georgia,serif;font-weight:400;font-size:76px;line-height:1.02;letter-spacing:-3.7px;margin:18px 0 20px}.dot{color:var(--green)}.project{color:var(--muted);font-size:16px}h2{font-size:23px;font-weight:600;letter-spacing:-.7px;line-height:1.3;margin:10px 0}h3{font-size:15px;font-weight:600;line-height:1.4}p{margin:8px 0}.verdict{display:flex;justify-content:space-between;gap:30px;align-items:center;border:1px solid #c5d4c2;border-left:4px solid var(--green);border-radius:4px;padding:24px 28px;background:#ecf1e6}.verdict p{font-size:13px;color:#53644f;max-width:740px}.delta{display:grid;min-width:105px;text-align:center;line-height:1.3}.delta strong{font-size:44px;font-weight:600;color:var(--green);letter-spacing:-2px}.delta span{font-size:11px;color:#52694a}.delta b{font-size:11px;font-weight:500;margin-top:8px}.arms{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:16px;margin:22px 0}.arm{border:1px solid var(--line);border-radius:5px;padding:22px;background:#fdfcf8;min-width:0}.arm-top{display:flex;justify-content:space-between;gap:12px;align-items:center}.letter{display:inline-grid;place-items:center;border:1px solid #bec8b8;border-radius:50%;width:29px;height:29px;font-size:12px;font-weight:700}.small{width:24px;height:24px}.state{font-size:10px;color:var(--muted);overflow-wrap:anywhere}.arm h3{margin:17px 0 7px}.score{font-size:51px;font-weight:550;line-height:1.3;letter-spacing:-2px}.score>span{font-size:25px;color:#93998c;font-weight:400}.score small{display:block;font-size:11px;letter-spacing:0;font-weight:400;color:var(--muted)}.bars{display:flex;gap:4px;margin:18px 0 21px}.bars i{height:5px;flex:1;border-radius:1px}.ok{background:#4f875e}.bad{background:#d79f7c}.arm-foot{display:flex;justify-content:space-between;font-size:12px;border-top:1px solid var(--line);padding-top:12px}.model{font:10px/1.4 ui-monospace,monospace;color:var(--muted);overflow-wrap:anywhere;margin-top:12px}.budget{display:grid;grid-template-columns:1fr 1fr;gap:12px 38px;border:1px solid var(--line);border-radius:5px;padding:20px 24px}.budget h3{font-size:22px;margin:6px 0}.budget h3 small{font-size:11px;color:var(--muted);font-weight:400}.meter{background:#e5e8dc;height:4px;max-width:300px;border-radius:5px;overflow:hidden}.meter i{display:block;height:100%;background:#617754}.budget>div:nth-child(2){display:flex;flex-direction:column;text-align:right;justify-content:center}.budget>div>strong{font-size:22px}.budget>div>span:not(.eyebrow){font-size:11px;color:var(--muted)}.budget p{grid-column:1/-1;font-size:10px;color:var(--muted);margin:0}.section{margin-top:52px}.section-heading{display:flex;justify-content:space-between;align-items:end;gap:16px;margin-bottom:20px}.filters{display:flex;gap:3px;border:1px solid var(--line);padding:3px;border-radius:5px}button,select{font:inherit;color:inherit;cursor:pointer}button{border:0;background:transparent}.filters button{padding:5px 10px;font-size:11px;border-radius:3px}.filters button.active{background:#253d30;color:#fff}.table-wrap{overflow:auto;border:1px solid var(--line);border-radius:5px}table{width:100%;border-collapse:collapse;text-align:left;font-size:12px}thead{font-size:10px;letter-spacing:.04em;background:#eceee5;color:#65705e}td,th{padding:13px 18px;border-bottom:1px solid var(--line)}tbody tr:last-child>*{border-bottom:0}th{font-weight:500}thead th:not(:first-child),td{text-align:center}tbody th{min-width:240px}td{min-width:87px}.badge{font-size:9px;font-weight:750;letter-spacing:.06em;border-radius:3px;padding:4px 7px}.pass{background:#e1ecdf;color:#316043}.fail{background:#f0e0d4;color:#965231}.unknown{background:#e7e7e1;color:#70746b}.time{display:block;color:#919688;font-size:9px;margin-top:4px}.holdout{font-size:8px;margin-left:8px;color:#7d876e;border:1px solid #cbd3c1;border-radius:3px;padding:2px 4px;white-space:nowrap}.caption{font-size:11px;color:var(--muted);line-height:1.6;margin-top:14px}.shots{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:14px}[hidden]{display:none!important}figure{margin:0;min-width:0}figcaption{display:flex;gap:8px;align-items:center;font-size:11px;margin:6px 0 12px}.zoom{display:block;padding:0;width:100%;border:1px solid var(--line);border-radius:5px;overflow:hidden;background:#e8ebe3}.zoom img{display:block;width:100%;height:auto}.select-label{font-size:10px;color:var(--muted);white-space:nowrap}select{font-size:11px;padding:7px;border:1px solid var(--line);border-radius:4px;background:#fafaf5;margin-left:8px}details{border:1px solid var(--line);border-radius:5px;margin-top:12px;padding:14px 18px}summary{font-size:12px;cursor:pointer;font-weight:600;overflow-wrap:anywhere}summary span{font-size:10px;color:var(--muted);font-weight:400;margin-left:10px}.intent p{font-size:13px;max-width:850px;padding-top:10px}pre{white-space:pre-wrap;overflow-wrap:anywhere;max-height:520px;overflow:auto;font:11px/1.7 ui-monospace,SFMono-Regular,monospace;padding:16px;background:#eceee5;border-radius:4px}footer{display:grid;grid-template-columns:1fr auto;gap:8px 20px;border-top:1px solid var(--line);padding:30px 0 40px;margin-top:52px;font-size:11px;color:var(--muted)}footer strong{font-size:13px;color:#334030}footer p{grid-row:2}footer>span{font-size:10px}.error{font-size:11px;color:#915131;overflow-wrap:anywhere}dialog{border:1px solid #aebaa3;border-radius:8px;max-width:95vw;width:1240px;padding:14px;background:#f6f5ef}dialog::backdrop{background:#142518c4}dialog img{width:100%;height:auto;display:block}#close-dialog{display:block;margin:0 0 10px auto;padding:5px 9px;font-size:12px}button:focus-visible,summary:focus-visible,select:focus-visible{outline:2px solid #488362;outline-offset:4px}@media(max-width:700px){main{padding:0 20px}header{padding:20px 0}.brand{font-size:13px}.brand span{display:none}.status-label{font-size:8px}h1{font-size:54px;letter-spacing:-2.5px}.hero{padding-top:36px}.verdict{padding:20px;gap:14px}.verdict h2{font-size:21px}.delta{min-width:74px}.delta strong{font-size:36px}.arms{grid-template-columns:1fr}.arm{padding:20px}.score{font-size:43px}.budget{grid-template-columns:1fr;padding:20px}.budget>div:nth-child(2){text-align:left}.section-heading{align-items:start;flex-direction:column}h2{font-size:21px}.shots{grid-template-columns:1fr}summary span{display:block;margin-left:0;margin-top:5px}footer{grid-template-columns:1fr}footer>span{grid-row:3}.hero .project{font-size:13px}.verdict p{font-size:12px}}@media(prefers-reduced-motion:no-preference){.zoom:hover img{filter:brightness(.97)}}
"""

SCRIPT = """
document.querySelectorAll('[data-filter]').forEach(button=>button.addEventListener('click',()=>{
  document.querySelectorAll('[data-filter]').forEach(b=>{b.classList.toggle('active',b===button);b.setAttribute('aria-pressed',b===button?'true':'false')});
  document.querySelectorAll('tr[data-changed]').forEach(row=>{row.hidden=button.dataset.filter!=='all'&&row.dataset[button.dataset.filter]!=='true'});
}));
document.querySelector('#shot-state').addEventListener('change',event=>{
  document.querySelectorAll('[data-shot]').forEach(el=>{el.hidden=el.dataset.shot!==event.target.value});
});
const dialog=document.querySelector('#lightbox');
document.querySelectorAll('.zoom').forEach(button=>button.addEventListener('click',()=>{
  const source=button.querySelector('img');dialog.querySelector('img').src=source.src;dialog.querySelector('img').alt=source.alt;dialog.showModal();
}));
document.querySelector('#close-dialog').addEventListener('click',()=>dialog.close());
dialog.addEventListener('click',event=>{if(event.target===dialog)dialog.close()});
"""
