"""Create a capsule from an explicit HTML artifact, intent and independent checks."""

from __future__ import annotations

import os
from pathlib import Path
import re

from .artifacts import capture_artifact
from .core import CapsuleError, load_capsule, safe_relative, validate_checks, write_json


def capture_html(path: Path, intent: str, checks: list, output: Path, *, scripts_only: bool = False,
                 confirmed: bool = False, provenance: dict | None = None, failures: list[str] | None = None,
                 constraints: list[str] | None = None) -> Path:
    path, output = Path(path).absolute(), Path(output).absolute()
    if path.is_symlink() or not path.is_file():
        raise CapsuleError("Select a regular HTML file, not a symlink")
    if path.suffix.lower() not in {".html", ".htm"}:
        raise CapsuleError("Capture currently supports a self-contained HTML file")
    safe_relative(path.name)
    if output.exists():
        raise CapsuleError(f"Capsule already exists: {output}")
    if output.resolve().is_relative_to(path.parent.resolve()):
        raise CapsuleError("Store the capsule outside the source directory")
    if not isinstance(intent, str) or not intent.strip() or len(intent) > 32_000:
        raise CapsuleError("Intent must be nonempty and at most 32,000 characters")
    validate_checks(checks)
    slug = re.sub(r"[^a-zA-Z0-9_-]", "-", path.stem)[:70] or "html-revisit"
    source = "User-supplied capture intent"
    if provenance:
        source = f"Selected human request in {provenance.get('session_id', 'local source')}, line {provenance.get('line', '?')}"
    capsule = {"version": 1, "id": slug, "title": path.stem + " revisit",
               "root": os.path.relpath(path.parent.resolve(), output.parent.resolve()), "entrypoint": path.name, "files": [path.name],
               "context": {path.name: {"mode": "html_scripts"}} if scripts_only else {},
               "intent": {"text": intent, "source": source, "confirmed": confirmed, "provenance": provenance or {"kind": "user_supplied"}},
               "baseline": {"model": "unknown", "provenance": "User-selected local artifact; origin and historical model unverified"},
               "constraints": constraints or ["Preserve existing data, useful behavior, input selectors and offline operation."],
               "assumptions": [], "failures": failures or [], "checks": checks,
               "revisit": {"capabilities": ["coding", "accessibility"], "impact": 3, "estimated_usd": 2.0}}
    # Check scope and size before writing the new capsule.
    capture_artifact({**capsule, "_root": str(path.parent.resolve())})
    write_json(output, capsule)
    try:
        load_capsule(output)
    except Exception:
        output.unlink()
        raise
    return output


def inspect_artifact(capsule_path: Path) -> dict:
    capsule = load_capsule(capsule_path)
    artifact = capture_artifact(capsule)
    return {"id": capsule["id"], "intent_confirmed": capsule["intent"]["confirmed"], "checks": len(capsule["checks"]),
            "source_identity": artifact.identity, "source": artifact.metrics, "model_calls": 0,
            "note": "Only selected context is sent in a future live run; this inspection sends nothing."}
