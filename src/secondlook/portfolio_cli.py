"""CLI entry points for the local problem portfolio."""

from __future__ import annotations

import json
from pathlib import Path
import sys

from .board import write_board
from .catalog import CATALOG_URL, MAX_CATALOG_BYTES, fetch_catalog
from .core import CapsuleError
from .library import Library
from .portfolio import execute_plan, make_plan, reconcile_plan
from .runner import MODES

COMMANDS = {"harvest", "restore", "candidate", "watch", "queue", "revisit", "reconcile", "board", "portfolio-demo"}


def add_commands(commands):
    for name in sorted(COMMANDS - {"portfolio-demo"}):
        help_text = {"harvest": "Preserve a problem/capsule without model calls", "candidate": "Register explicit model and capability claims",
                     "watch": "Observe model catalog once; optionally prepare queues (no model calls)",
                     "queue": "Save an explained budgeted revisit plan", "revisit": "Execute one saved plan; never replay automatically",
                     "reconcile": "Reconcile terminal local evidence without replay", "board": "Render the local problem and outcome board",
                     "restore": "Restore an immutable original artifact revision into a new directory"}[name]
        command = commands.add_parser(name, help=help_text)
        command.add_argument("--library", type=Path, default=Path(".secondlook/library"))
        if name in {"harvest", "candidate"}:
            command.add_argument("input", type=Path)
        if name == "harvest":
            command.add_argument("--problem", action="store_true", help="Input is a general problem record, not an executable capsule")
        if name == "restore":
            command.add_argument("task")
            command.add_argument("--revision")
            command.add_argument("--output", type=Path, required=True)
        if name == "watch":
            command.add_argument("--catalog", type=Path, help="Use an explicit saved catalog instead of the public API")
            command.add_argument("--source", help="Stable catalog identity for saved snapshots")
            command.add_argument("--queue", action="store_true", help="Prepare plans for explicitly mapped changed candidates; never execute")
            command.add_argument("--budget-usd", type=float, default=2, help="Stop budget per prepared candidate plan")
        if name == "queue":
            command.add_argument("candidate")
            command.add_argument("--budget-usd", type=float, default=2)
            command.add_argument("--mode", choices=MODES, default="reframe")
            command.add_argument("--trial", type=int, default=1, help="Explicit different trial number authorizes fresh eligibility, not automatic dispatch")
        if name in {"revisit", "reconcile"}:
            command.add_argument("plan")
    demo = commands.add_parser("portfolio-demo", help="Run a labeled multi-project simulation and real browser checks, without models")
    demo.add_argument("--output", type=Path, required=True)


def read_json(path: Path, maximum: int = 2 * 1024 * 1024):
    with path.open("rb") as stream:
        raw = stream.read(maximum + 1)
    if len(raw) > maximum:
        raise CapsuleError(f"Input exceeds {maximum} bytes")
    return json.loads(raw)


def watch_catalog(library: Library, payload: dict, source: str, budget: float = 2, queue: bool = False) -> dict:
    observed = library.sync_catalog(payload, source)
    plans = []
    if queue:
        events = {event["model_id"]: event for event in observed["events"] if event["kind"] != "removed"}
        for candidate in library.list("candidate"):
            if candidate.get("catalog_source") == source and candidate.get("catalog_id") in events:
                plans.append(make_plan(library, candidate["id"], budget, trigger=events[candidate["catalog_id"]]))
    return {**observed, "plans": plans}


def compact_plan(plan: dict) -> dict:
    return {key: value for key, value in plan.items() if key != "selected"} | {
        "selected": [{key: value for key, value in item.items() if key != "record"} for item in plan["selected"]]}


def handle(args) -> int:
    if args.command == "portfolio-demo":
        from .portfolio_demo import portfolio_demo
        data = portfolio_demo(args.output)
        data = {"simulation": True, "board": data["board"], "campaign": data["campaign"],
                "repeat_decisions": data["repeat"]["decisions"]}
    else:
        library = Library(args.library)
        if args.command == "harvest":
            record = library.harvest_problem(read_json(args.input)) if args.problem else library.harvest_capsule(args.input)
            data = {"id": record["id"], "revision": record["revision"], "adapter": record["adapter"], "model_calls": 0}
        elif args.command == "restore":
            data = {"capsule": str(library.restore(args.task, args.output, args.revision)), "model_calls": 0}
        elif args.command == "candidate":
            data = {**library.register_candidate(read_json(args.input)), "model_calls": 0}
        elif args.command == "watch":
            payload = read_json(args.catalog, MAX_CATALOG_BYTES) if args.catalog else fetch_catalog()
            source = args.source or ("file:" + str(args.catalog.resolve()) if args.catalog else CATALOG_URL)
            data = watch_catalog(library, payload, source, args.budget_usd, args.queue)
            data["plans"] = [compact_plan(plan) for plan in data["plans"]]
        elif args.command == "queue":
            data = compact_plan(make_plan(library, args.candidate, args.budget_usd, args.mode, args.trial))
        elif args.command == "revisit":
            data = execute_plan(library, args.plan, progress=lambda message: print(message, file=sys.stderr, flush=True))
        elif args.command == "reconcile":
            data = reconcile_plan(library, args.plan)
        else:
            data = {"model_calls": 0}
        data["board"] = str(write_board(library))
    print(json.dumps(data, ensure_ascii=False, indent=2))
    return 1 if data.get("status") in {"needs_reconciliation", "stopped_budget", "stopped_stale_source"} else 0
