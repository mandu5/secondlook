"""Small, explicit command-line surface for local revisit experiments."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sqlite3
import sys

from . import __version__
from .capture import capture_html, inspect_artifact
from .diagnostics import diagnose
from .core import CapsuleError, load_capsule, plan_capsules, positive_number, source_bundle, write_json
from .fixtures import create_demo
from .report import write_report
from .runner import MODES, probe, run
from .sessions import read_requests, select_request
from .sharing import share_result
from .handoff import MAX_REQUEST_BYTES, prepare_request, read_json
from .assessment import assess_responses
from .portfolio_cli import COMMANDS, add_commands, handle


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="secondlook", description="Revisit old AI work. Measure what actually improves.")
    root.add_argument("--version", action="version", version=__version__)
    commands = root.add_subparsers(dest="command", required=True)
    add_commands(commands)
    doctor = commands.add_parser("doctor", help="Check Python and launch Chromium locally; no model calls")
    doctor.add_argument("--provider", action="store_true", help="Also check Claude CLI flags; does not verify authentication or model availability")
    capture = commands.add_parser("capture", help="Capture a local HTML artifact with explicit intent and checks; no model calls")
    capture.add_argument("html", type=Path)
    capture.add_argument("--checks", required=True, type=Path, help="JSON array of independent browser checks")
    intent = capture.add_mutually_exclusive_group(required=True)
    intent.add_argument("--intent")
    intent.add_argument("--session", type=Path, help="Explicit local Codex/Claude JSONL session")
    capture.add_argument("--request-line", type=int, help="Physical line selected with requests")
    capture.add_argument("--scripts-only", action="store_true", help="Model sees only executable inline scripts; full HTML runs locally")
    capture.add_argument("--confirm-intent", action="store_true", help="Confirm that the selected request and scope are appropriate for this artifact")
    capture.add_argument("--failure", action="append", default=[])
    capture.add_argument("--constraint", action="append", default=[])
    capture.add_argument("--output", type=Path, default=Path("capsule.json"))
    requests = commands.add_parser("requests", help="Read bounded human request previews from an explicit local session; no model calls")
    requests.add_argument("session", type=Path)
    requests.add_argument("--line", type=int, help="Show the complete selected human request and its provenance")
    inspect = commands.add_parser("inspect", help="Show source/context byte sizes and identity; no model calls")
    inspect.add_argument("capsule", type=Path)
    probe_parser = commands.add_parser("probe", help="Run browser checks only, even with draft intent; no model calls")
    probe_parser.add_argument("capsule", type=Path)
    probe_parser.add_argument("--output", type=Path)
    prepare = commands.add_parser("prepare", help="Freeze a task and export a request for your existing AI tool; no model calls")
    prepare.add_argument("capsule", type=Path)
    prepare.add_argument("--mode", choices=("ordinary", "rebuild"), default="rebuild")
    prepare.add_argument("--output", type=Path, required=True)
    assess = commands.add_parser("assess", help="Compare imported responses locally against frozen checks; no model calls")
    assess.add_argument("request", type=Path, help="Directory written by prepare")
    assess.add_argument("--response", type=Path, action="append", required=True, help="Response JSON; repeat for up to four candidates")
    assess.add_argument("--label", action="append", required=True, help="Owner-reported model/tool label; one per response, in the same order")
    assess.add_argument("--usage", type=Path, help="Optional same-order JSON array of owner-reported cost/token records; unknown by default")
    assess.add_argument("--output", type=Path, required=True)
    init = commands.add_parser("init", help="Capture original intent and a source allowlist")
    init.add_argument("root", type=Path)
    init.add_argument("--intent", required=True)
    init.add_argument("--files", nargs="+", required=True)
    init.add_argument("--entrypoint", default="index.html")
    init.add_argument("--output", type=Path, default=Path("capsule.json"))
    init.add_argument("--expect-text", nargs=2, action="append", default=[], metavar=("SELECTOR", "TEXT"), help="Explicit goal: exact text at a Playwright selector; repeatable")
    init.add_argument("--preserve-text", nargs=2, action="append", default=[], metavar=("SELECTOR", "TEXT"), help="Explicit behavior to keep: exact text at a selector; repeatable")
    init.add_argument("--brief-file", type=Path, help="Independent requirements for clean-slate comparison; requires both types of check")
    init.add_argument("--confirm-intent", action="store_true", help="Confirm the supplied intent, criteria and optional independent brief after review")
    plan = commands.add_parser("plan", help="Select tasks using declared impact, capabilities and cost")
    plan.add_argument("capsules", nargs="+", type=Path)
    plan.add_argument("--capability", action="append", default=[])
    plan.add_argument("--budget-usd", type=float, default=2.0)
    for name, help_text in (("run", "Evaluate a capsule with a bounded model experiment"), ("demo", "Run the public synthetic feedback example")):
        command = commands.add_parser(name, help=help_text)
        if name == "run":
            command.add_argument("capsule", type=Path)
        else:
            command.add_argument("--offline", action="store_true", help="Use a labeled hand-authored repair; no model call")
        command.add_argument("--output", type=Path, help="New output directory outside the source root")
        command.add_argument("--model", default="sonnet")
        command.add_argument("--budget-usd", type=float, default=2.0, help="Total API-equivalent stop budget, split equally across selected candidate arms")
        command.add_argument("--mode", choices=MODES, default="compare")
        command.add_argument("--force", action="store_true", help="Run even when the baseline passes every captured check")
    report = commands.add_parser("report", help="Rebuild a report from existing evidence without model calls")
    report.add_argument("result", type=Path)
    share = commands.add_parser("share", help="Export portable metrics without source, prompts or local paths; no model calls")
    share.add_argument("result", type=Path)
    share.add_argument("--output", type=Path, required=True)
    share.add_argument("--title", default="Second Look comparison")
    share.add_argument("--include-intent", action="store_true", help="Explicitly include original intent text")
    share.add_argument("--include-screenshots", action="store_true", help="Explicitly embed screenshots; visible page content will be shared")
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command in COMMANDS:
            return handle(args)
        if args.command == "doctor":
            result = diagnose(provider=args.provider)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0 if result["ready"] else 1
        elif args.command == "requests":
            session = read_requests(args.session)
            if args.line is not None:
                data = select_request(session, args.line)
            else:
                data = {**session, "requests": [{**request, "text": request["text"][:240],
                                                  "preview_truncated": len(request["text"]) > 240} for request in session["requests"]]}
            print(json.dumps(data, ensure_ascii=False, indent=2))
        elif args.command == "capture":
            provenance = None
            if args.session:
                if args.request_line is None:
                    raise CapsuleError("Select --request-line explicitly; list human requests with secondlook requests")
                request = select_request(read_requests(args.session), args.request_line)
                intent_text = request["text"]
                provenance = {k: v for k, v in request.items() if k != "text"}
            else:
                if args.request_line is not None:
                    raise CapsuleError("--request-line requires --session")
                intent_text = args.intent
            checks = json.loads(args.checks.read_text(encoding="utf-8"))
            path = capture_html(args.html, intent_text, checks, args.output, scripts_only=args.scripts_only,
                                confirmed=args.confirm_intent, provenance=provenance, failures=args.failure,
                                constraints=args.constraint)
            print(json.dumps({"capsule": str(path), "intent_confirmed": args.confirm_intent, "model_calls": 0}, indent=2))
        elif args.command == "inspect":
            print(json.dumps(inspect_artifact(args.capsule), ensure_ascii=False, indent=2))
        elif args.command == "prepare":
            result = prepare_request(args.capsule, args.output, mode=args.mode)
            print(json.dumps({"request_id": result["request_id"], "request": str(args.output.resolve() / "request.md"),
                              "mode": args.mode, "model_calls": 0, "note": result["note"]}, ensure_ascii=False, indent=2))
        elif args.command == "assess":
            usage = read_json(args.usage, MAX_REQUEST_BYTES) if args.usage else None
            result = assess_responses(args.request, args.response, args.label, args.output, usage=usage)
            report_path = write_report(result, args.output.resolve())
            print(json.dumps({"status": result["status"], "report": str(report_path), "model_calls": 0,
                              "cost": result["cost"], "comparisons": result["comparisons"]}, ensure_ascii=False, indent=2))
            return 0 if result["status"] == "completed" else 1
        elif args.command == "probe":
            stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
            output = (args.output or Path(".secondlook") / (stamp + "-probe")).resolve()
            evidence = probe(args.capsule, output, progress=lambda message: print(message, file=sys.stderr, flush=True))
            report_path = write_report(evidence, output)
            print(json.dumps({"status": evidence["status"], "report": str(report_path), "cost": evidence["cost"],
                              "passed": evidence["arms"]["A"]["evaluation"]["passed"], "model_calls": 0}, indent=2))
            if evidence["status"] != "probe_completed":
                return 1
        elif args.command == "init":
            output = args.output.resolve()
            if args.output.is_symlink() or output.exists():
                raise CapsuleError(f"Capsule already exists: {output}")
            root = args.root.resolve()
            slug = re.sub(r"[^a-zA-Z0-9_-]", "-", root.name)[:70] or "revisit"
            capsule = {"version": 1, "id": slug, "title": root.name + " revisit", "root": os.path.relpath(root, output.parent),
                       "intent": {"text": args.intent, "source": "User supplied via secondlook init", "confirmed": args.confirm_intent},
                       "files": args.files, "entrypoint": args.entrypoint,
                       "baseline": {"model": "unknown", "provenance": "Existing user-selected artifact"},
                       "constraints": ["Preserve useful behavior and offline operation."], "assumptions": [], "failures": [],
                       "revisit": {"capabilities": ["coding"], "impact": 3, "estimated_usd": 2.0},
                       "checks": [{"id": "page-visible", "name": "Page body is visible (replace with product checks)",
                                   "actions": [], "assert": {"selector": "body", "visible": True}}]}
            if args.expect_text or args.preserve_text:
                capsule["checks"] = [
                    {"id": f"{category}-{index}", "category": category,
                     "basis": "Owner-supplied acceptance criterion via secondlook init",
                     "name": f"{category.title()} {index}: {expected}", "actions": [],
                     "assert": {"selector": selector, "text": expected}, "capture": True}
                    for category, pairs in (("intent", args.expect_text), ("preservation", args.preserve_text))
                    for index, (selector, expected) in enumerate(pairs, 1)
                ]
            if args.brief_file:
                if not args.expect_text or not args.preserve_text:
                    raise CapsuleError("--brief-file requires at least one --expect-text and --preserve-text")
                if args.brief_file.stat().st_size > 16_384:
                    raise CapsuleError("Independent rebuild brief exceeds 16 KiB")
                capsule["rebuild"] = {"brief": args.brief_file.read_text(encoding="utf-8"),
                                      "source": "Owner-supplied independent requirements file",
                                      "confirmed": args.confirm_intent}
            # Validate before exposing a usable capsule; source remains read-only.
            write_json(output, capsule)
            try:
                source_bundle(load_capsule(output))
            except Exception:
                output.unlink()
                raise
            state = "Confirmed" if args.confirm_intent else "Draft"
            print(f"{state} capsule: {output}\nRun secondlook probe {output} --output .secondlook/baseline (no model calls).")
            if not args.confirm_intent:
                print("Review intent and acceptance checks, then set intent.confirmed to true before a model run.")
        elif args.command == "plan":
            print(json.dumps({"method": "Declared impact / declared cost; heuristic, not predicted model uplift",
                              "selected": plan_capsules(args.capsules, set(args.capability), args.budget_usd)}, ensure_ascii=False, indent=2))
        elif args.command == "report":
            evidence = json.loads(args.result.read_text(encoding="utf-8"))
            print(write_report(evidence, args.result.resolve().parent))
        elif args.command == "share":
            path = share_result(args.result, args.output, title=args.title, include_intent=args.include_intent,
                                include_screenshots=args.include_screenshots)
            print(json.dumps({"report": str(path), "model_calls": 0,
                              "intent_included": args.include_intent, "screenshots_included": args.include_screenshots}, indent=2))
        else:
            positive_number(args.budget_usd, "budget")
            stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
            output = (args.output or Path(".secondlook") / stamp).resolve()
            if output.exists() and any(output.iterdir()):
                raise CapsuleError(f"Output already exists and is not empty: {output}")
            capsule_path = args.capsule if args.command == "run" else create_demo(output.with_name(output.name + "-input"))
            evidence = run(capsule_path, output, model=args.model, budget=args.budget_usd, mode=args.mode,
                           offline=getattr(args, "offline", False), force=args.force,
                           progress=lambda message: print(message, file=sys.stderr, flush=True))
            report_path = write_report(evidence, output)
            print(json.dumps({"status": evidence["status"], "report": str(report_path), "cost": evidence["cost"],
                              "comparisons": evidence["comparisons"]}, ensure_ascii=False, indent=2))
            if evidence["status"] not in {"completed", "skipped_baseline_passes"}:
                return 1
        return 0
    except (CapsuleError, OSError, ValueError, KeyError, sqlite3.Error) as error:
        print(f"secondlook: {error}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Interrupted. Inspect existing receipts before another logical request.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
