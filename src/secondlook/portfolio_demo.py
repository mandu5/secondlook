"""A labeled, reproducible portfolio demonstration: no historical model claims."""

from pathlib import Path
import json

from .board import write_board
from .core import CapsuleError, write_json
from .fixtures import create_demo
from .library import Library
from .portfolio import execute_plan, make_plan


def seed_portfolio(destination: Path, runtime_model: str = "claude-demo-simulation") -> Library:
    destination = Path(destination).resolve()
    if destination.exists() and any(destination.iterdir()):
        raise CapsuleError("Portfolio destination must be empty")
    destination.mkdir(parents=True, exist_ok=True)
    library = Library(destination / "library")
    path = create_demo(destination / "projects" / "feedback")
    capsule = json.loads(path.read_text())
    capsule.update(id="feedback-board", title="Customer feedback board")
    capsule["revisit"] = {"capabilities": ["coding"], "impact": 5, "estimated_usd": 0.45}
    write_json(path, capsule)
    library.harvest_capsule(path)
    timer = destination / "projects" / "timer"
    timer.mkdir(parents=True)
    (timer / "index.html").write_text('''<!doctype html><html lang="en"><meta charset="utf-8"><title>Focus timer</title>
<h1>Focus timer</h1><label>Minutes <input id="minutes" type="number" value="25"></label>
<button id="start">Start</button><button id="reset">Reset</button><p id="remaining">25:00</p>
<script>document.querySelector('#start').onclick=()=>{document.querySelector('#remaining').textContent=document.querySelector('#minutes').value+':00'};
document.querySelector('#reset').onclick=()=>{document.querySelector('#remaining').textContent='25:00'};</script></html>''')
    timer_capsule = {"version": 1, "id": "focus-timer", "title": "Personal focus timer", "root": ".", "files": ["index.html"],
        "entrypoint": "index.html", "intent": {"text": "Set a positive whole number of minutes and reset both input and display to 25 minutes.",
        "source": "Synthetic user brief for this demo", "confirmed": True},
        "baseline": {"model": "unknown", "provenance": "Hand-authored faulty demonstration"},
        "constraints": ["Keep the existing controls and IDs", "No network dependency"],
        "failures": ["Reset leaves the duration input unchanged", "Negative minutes are accepted"],
        "assumptions": [{"text": "Changing only the display is a complete reset", "source": "Legacy implementation behavior"}],
        "revisit": {"capabilities": ["coding"], "impact": 3, "estimated_usd": 0.6},
        "checks": [{"id": "initial", "assert": {"selector": "#remaining", "text": "25:00"}},
                   {"id": "duration", "actions": [{"type": "fill", "selector": "#minutes", "value": "10"}, {"type": "click", "selector": "#start"}], "assert": {"selector": "#remaining", "text": "10:00"}},
                   {"id": "reset-input", "actions": [{"type": "fill", "selector": "#minutes", "value": "10"}, {"type": "click", "selector": "#reset"}], "assert": {"selector": "#minutes", "value": "25"}}]}
    write_json(timer / "capsule.json", timer_capsule)
    library.harvest_capsule(timer / "capsule.json")
    library.harvest_problem({"id": "research-note", "title": "A disputed research finding", "kind": "research",
        "intent": {"text": "Determine whether the finding holds across independent datasets, with sources that can be checked.",
                   "source": "Synthetic research brief", "confirmed": True},
        "constraints": ["Preserve negative evidence and uncertainty"], "failures": ["No independently reviewed evaluation rubric yet"],
        "assumptions": [{"text": "One benchmark generalizes to other domains", "source": "Legacy draft hypothesis"}],
        "revisit": {"capabilities": ["research", "long-context"], "impact": 4, "estimated_usd": 0.3}})
    library.register_candidate({"id": "candidate", "runtime_model": runtime_model, "revision": "explicit-demo-profile-1",
        "provider": "claude-cli", "capabilities": ["coding"],
        "evidence": "Demonstration configuration; capability overlap is not evidence of improved performance",
        "catalog_id": "demo/candidate", "catalog_source": "simulation:portfolio"})
    return library


def portfolio_demo(destination: Path) -> dict:
    library = seed_portfolio(destination)
    library.sync_catalog({"data": [{"id": "demo/previous"}]}, "simulation:portfolio")
    observed = library.sync_catalog({"data": [{"id": "demo/previous"}, {"id": "demo/candidate"}]}, "simulation:portfolio")
    plan = make_plan(library, "candidate", 0.5, offline=True, trigger=observed["events"][0])
    campaign = execute_plan(library, plan["id"])
    repeat = make_plan(library, "candidate", 0.5, offline=True)
    return {"simulation": True, "board": str(write_board(library)), "campaign": campaign, "repeat": repeat}
