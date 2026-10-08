"""Capsules, content identity, and narrowly scoped source edits."""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import tempfile


MAX_CONTEXT_BYTES = 65_536
SAFE_SUFFIXES = {".html", ".htm", ".js", ".mjs", ".css", ".json", ".svg", ".txt"}


class CapsuleError(ValueError):
    """A capsule or edit cannot safely be used."""


def positive_number(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise CapsuleError(f"{label} must be a finite positive number")
    return float(value)


def fingerprint(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(encoded.encode()).hexdigest()


def write_json(path: Path, value: object) -> None:
    atomic_text(path, json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def atomic_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def safe_relative(name: str) -> Path:
    if not isinstance(name, str) or not name or "\\" in name or "\x00" in name:
        raise CapsuleError(f"Unsafe source path: {name!r}")
    path = PurePosixPath(name)
    if path.is_absolute() or str(path) != name or any(p.startswith(".") or ":" in p for p in path.parts):
        raise CapsuleError(f"Unsafe source path: {name!r}")
    if path.suffix.lower() not in SAFE_SUFFIXES or path.stem.lower() in {"credentials", "secrets", "id_rsa", "id_ed25519"}:
        raise CapsuleError(f"Source type or private filename refused: {name}")
    return Path(*path.parts)


def source_path(root: Path, name: str) -> Path:
    rel = safe_relative(name)
    current = root
    for part in rel.parts:
        current = current / part
        if current.is_symlink():
            raise CapsuleError(f"Source symlink refused: {name}")
    if not current.resolve().is_relative_to(root.resolve()):
        raise CapsuleError(f"Source escapes root: {name}")
    return current


def _strings(value: object, label: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(s, str) or not s for s in value):
        raise CapsuleError(f"{label} must be a list of nonempty strings")
    return value


def validate_checks(checks: object, readonly_files: list[str] | None = None) -> None:
    if not isinstance(checks, list) or not 1 <= len(checks) <= 50:
        raise CapsuleError("Provide between 1 and 50 independent checks")
    seen = set()
    for check in checks:
        if not isinstance(check, dict) or not isinstance(check.get("id"), str) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", check["id"]):
            raise CapsuleError("Each check needs a safe id")
        if check["id"] in seen:
            raise CapsuleError("Check ids must be unique")
        seen.add(check["id"])
        if "inputs" in check:
            inputs = check["inputs"]
            if not isinstance(inputs, dict) or not inputs:
                raise CapsuleError("Check inputs must be a nonempty mapping of read-only JSON files to data")
            for name, value in inputs.items():
                if name not in (readonly_files or []) or not name.lower().endswith(".json") or not isinstance(value, (dict, list)):
                    raise CapsuleError("Check inputs may override only declared read-only JSON files with objects/arrays")
                safe_relative(name)
            try:
                size = len(json.dumps(inputs, ensure_ascii=False, allow_nan=False).encode("utf-8"))
            except (ValueError, TypeError) as error:
                raise CapsuleError("Check inputs must be finite JSON data") from error
            if size > MAX_CONTEXT_BYTES:
                raise CapsuleError("Check inputs exceed 64 KiB")
        if "category" in check:
            if check["category"] not in ("intent", "preservation"):
                raise CapsuleError("Check category must be intent or preservation")
            if not isinstance(check.get("basis"), str) or not check["basis"].strip():
                raise CapsuleError("Categorized checks need a nonempty provenance basis")
        for flag in ("held_out", "capture"):
            if flag in check and type(check[flag]) is not bool:
                raise CapsuleError(f"{flag} must be a boolean")
        if "viewport" in check:
            viewport = check["viewport"]
            if not isinstance(viewport, dict) or set(viewport) != {"width", "height"} or any(
                type(viewport[k]) is not int or not 240 <= viewport[k] <= 3840 for k in ("width", "height")
            ):
                raise CapsuleError("viewport needs integer width and height between 240 and 3840")
        assertion = check.get("assert")
        if not isinstance(assertion, dict) or not (set(assertion) & {"text", "count", "value", "visible", "csv", "focused", "attribute"}):
            raise CapsuleError("Each check needs a nonempty supported assertion")
        if set(assertion) - {"selector", "text", "count", "value", "visible", "csv", "focused", "attribute"}:
            raise CapsuleError("Unsupported assertion")
        if "csv" not in assertion and (not isinstance(assertion.get("selector"), str) or not assertion["selector"].strip()):
            raise CapsuleError("DOM assertions need a selector")
        if "csv" in assertion:
            rows = assertion["csv"]
            if set(assertion) != {"csv"} or not isinstance(rows, list) or any(
                not isinstance(row, list) or any(not isinstance(cell, str) for cell in row) for row in rows
            ):
                raise CapsuleError("CSV assertion must contain only csv: an array of string rows")
        if "count" in assertion and (type(assertion["count"]) is not int or assertion["count"] < 0):
            raise CapsuleError("count must be a nonnegative integer")
        if "visible" in assertion and type(assertion["visible"]) is not bool:
            raise CapsuleError("visible must be a boolean")
        if "focused" in assertion and type(assertion["focused"]) is not bool:
            raise CapsuleError("focused must be a boolean")
        if "attribute" in assertion:
            attribute = assertion["attribute"]
            if not isinstance(attribute, dict) or set(attribute) != {"name", "value"} or not isinstance(attribute["name"], str) or not re.fullmatch(r"[a-zA-Z_:][a-zA-Z0-9_.:-]*", attribute["name"]) or not isinstance(attribute["value"], str):
                raise CapsuleError("attribute needs a nonempty attribute name and string value")
        if "value" in assertion and not isinstance(assertion["value"], str):
            raise CapsuleError("value must be a string")
        if "text" in assertion and not (isinstance(assertion["text"], str) or (
            isinstance(assertion["text"], list) and all(isinstance(t, str) for t in assertion["text"])
        )):
            raise CapsuleError("text must be a string or list of strings")
        actions = check.get("actions", [])
        if not isinstance(actions, list) or len(actions) > 20:
            raise CapsuleError("A check can have at most 20 actions")
        for action in actions:
            if not isinstance(action, dict) or action.get("type") not in {"click", "fill", "select", "download", "focus", "press", "reload"}:
                raise CapsuleError("Unsupported browser action")
            if action["type"] == "reload":
                if set(action) != {"type"}:
                    raise CapsuleError("reload does not take a selector or arguments")
                continue
            if (action["type"] != "press" or "selector" in action) and (not isinstance(action.get("selector"), str) or not action["selector"].strip()):
                raise CapsuleError("Browser actions need a selector")
            if action["type"] == "press" and (not isinstance(action.get("key"), str) or not action["key"].strip() or len(action["key"]) > 100):
                raise CapsuleError("press needs a nonempty key of at most 100 characters")
            if action["type"] in {"fill", "select"} and not isinstance(action.get("value"), str):
                raise CapsuleError("Fill/select actions need a string value")
        if "csv" in assertion and not any(action["type"] == "download" for action in actions):
            raise CapsuleError("CSV assertion requires a download action")


def load_capsule(path: Path) -> dict:
    from .artifacts import validate_context
    path = Path(path).resolve()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise CapsuleError(f"Cannot read capsule: {error}") from error
    if not isinstance(data, dict) or data.get("version") != 1:
        raise CapsuleError("Expected capsule version 1")
    for key in ("id", "title", "root", "entrypoint"):
        if not isinstance(data.get(key), str) or not data[key].strip():
            raise CapsuleError(f"Capsule needs {key}")
    if not re.fullmatch(r"[a-zA-Z0-9_-]{1,80}", data["id"]):
        raise CapsuleError("Capsule id must use letters, numbers, hyphens or underscores")
    intent = data.get("intent")
    if not isinstance(intent, dict) or not isinstance(intent.get("text"), str) or not intent["text"].strip():
        raise CapsuleError("Record original intent.text before running")
    if not isinstance(intent.get("source"), str) or type(intent.get("confirmed")) is not bool:
        raise CapsuleError("Intent needs source and explicit confirmed boolean")
    files = _strings(data.get("files"), "files")
    if not 1 <= len(files) <= 32 or len(set(files)) != len(files):
        raise CapsuleError("Allowlist must have 1 to 32 unique files")
    for name in files:
        safe_relative(name)
    validate_context(data.get("context"), files)
    readonly = _strings(data.get("readonly_files", []), "readonly_files")
    if len(set(readonly)) != len(readonly) or set(readonly) - set(files) or data["entrypoint"] in readonly:
        raise CapsuleError("readonly_files must be unique allowlisted files excluding the entrypoint")
    rebuild = data.get("rebuild")
    if "rebuild" in data:
        if not isinstance(rebuild, dict) or set(rebuild) != {"brief", "source", "confirmed"}:
            raise CapsuleError("rebuild needs brief, source and confirmed")
        if any(not isinstance(rebuild[k], str) or not rebuild[k].strip() for k in ("brief", "source")) or type(rebuild["confirmed"]) is not bool:
            raise CapsuleError("rebuild needs nonempty brief/source and explicit confirmed boolean")
        if len(rebuild["brief"].encode("utf-8")) > 16_384:
            raise CapsuleError("Independent rebuild brief exceeds 16 KiB")
    if data["entrypoint"] not in files or Path(data["entrypoint"]).suffix not in {".html", ".htm"}:
        raise CapsuleError("Entrypoint must be an allowlisted HTML file")
    for key in ("constraints", "failures"):
        _strings(data.get(key, []), key)
    if not isinstance(data.get("assumptions", []), list):
        raise CapsuleError("Assumptions must be a list with provenance")
    revisit = data.get("revisit")
    if not isinstance(revisit, dict):
        raise CapsuleError("Capsule needs revisit estimates")
    _strings(revisit.get("capabilities"), "revisit.capabilities")
    positive_number(revisit.get("estimated_usd"), "estimated_usd")
    impact = positive_number(revisit.get("impact"), "impact")
    if impact > 5:
        raise CapsuleError("impact must be 1 through 5")
    validate_checks(data.get("checks"), readonly)
    root = (path.parent / data["root"]).resolve()
    if not root.is_dir():
        raise CapsuleError(f"Source root does not exist: {root}")
    data["_root"] = str(root)
    data["_path"] = str(path)
    return data


def public_capsule(capsule: dict) -> dict:
    return {k: v for k, v in capsule.items() if not k.startswith("_")}


def source_bundle(capsule: dict) -> dict[str, str]:
    from .artifacts import capture_artifact
    return capture_artifact(capsule).context


def write_bundle(root: Path, bundle: dict[str, str]) -> None:
    for name, content in bundle.items():
        atomic_text(source_path(root, name), content)


def require_rebuild(capsule: dict) -> None:
    """Check opt-in and evaluation coverage before reserving or dispatching work."""
    if not capsule.get("rebuild", {}).get("confirmed"):
        raise CapsuleError("Rebuild requires a confirmed independent rebuild brief")
    if capsule.get("context"):
        raise CapsuleError("Rebuild is unavailable for projected source context")
    categories = {check.get("category") for check in capsule["checks"]}
    if not {"intent", "preservation"} <= categories:
        raise CapsuleError("Rebuild requires intent and preservation checks with provenance")


def write_rebuild(root: Path, files: list, writable: list[str]) -> None:
    """Validate the entire replacement set, including size, before any file write."""
    if not isinstance(files, list) or len(files) != len(writable):
        raise CapsuleError("Rebuild must return every writable file exactly once")
    pending = {}
    for item in files:
        if not isinstance(item, dict) or set(item) != {"path", "content"} or not isinstance(item["path"], str):
            raise CapsuleError("Rebuild files need path and content")
        name = item["path"]
        if name not in writable or name in pending:
            raise CapsuleError("Rebuild file is read-only, duplicated or outside the allowlist")
        if not isinstance(item["content"], str) or not item["content"].strip():
            raise CapsuleError("Rebuild file content must be nonempty text")
        source_path(root, name)
        pending[name] = item["content"]
    if sum(len(content.encode("utf-8")) for content in pending.values()) > MAX_CONTEXT_BYTES:
        raise CapsuleError("Rebuild generated source exceeds 64 KiB")
    write_bundle(root, pending)


def apply_edits(root: Path, edits: list, allowed: list[str], context: dict | None = None) -> None:
    from .artifacts import artifact_from_sources, context_spans, validate_context
    policies = validate_context(context, allowed)
    if not isinstance(edits, list) or not 1 <= len(edits) <= 20:
        raise CapsuleError("Return 1 to 20 exact source edits")
    pending, regions, protected = {}, {}, {}
    for edit in edits:
        if not isinstance(edit, dict) or edit.get("path") not in allowed:
            raise CapsuleError("Edit is outside the source allowlist")
        path = source_path(root, edit["path"])
        if path not in pending:
            pending[path] = path.read_bytes().decode("utf-8")
            regions[path] = context_spans(pending[path], policies.get(edit["path"]))
            boundaries = [0] + [edge for pair in regions[path] for edge in pair] + [len(pending[path])]
            protected[path] = [pending[path][a:b] for a, b in zip(boundaries[::2], boundaries[1::2])]
        old, new = edit.get("old"), edit.get("new")
        if not isinstance(old, str) or not old or not isinstance(new, str):
            raise CapsuleError("Each edit needs nonempty old text and string new text")
        if pending[path].count(old) != 1:
            raise CapsuleError(f"Edit anchor must occur exactly once: {edit['path']}")
        start = pending[path].index(old)
        index = next((i for i, (left, right) in enumerate(regions[path]) if left <= start and start + len(old) <= right), None)
        if index is None:
            raise CapsuleError(f"Edit targets a protected region outside selected context: {edit['path']}")
        pending[path] = pending[path].replace(old, new, 1)
        delta = len(new) - len(old)
        regions[path] = [(left + (delta if i > index else 0), right + (delta if i >= index else 0))
                         for i, (left, right) in enumerate(regions[path])]
    # Authorization comes from the original partition, never from model-edited
    # markup. Re-parse only to verify the partition did not change interpretation.
    for name in allowed:
        path = source_path(root, name)
        if path not in pending:
            continue
        if name in policies and context_spans(pending[path], policies[name]) != regions[path]:
            raise CapsuleError(f"Edit changes selected script boundaries: {name}")
        boundaries = [0] + [edge for pair in regions[path] for edge in pair] + [len(pending[path])]
        after = [pending[path][a:b] for a, b in zip(boundaries[::2], boundaries[1::2])]
        if after != protected[path]:
            raise CapsuleError(f"Edit changes a protected region: {name}")
    candidate = {name: pending.get(source_path(root, name)) for name in allowed}
    candidate = {name: text if text is not None else source_path(root, name).read_bytes().decode("utf-8") for name, text in candidate.items()}
    artifact_from_sources(candidate, policies)
    # Validate the entire patch before writing any candidate file.
    for path, content in pending.items():
        atomic_text(path, content)


def plan_capsules(paths: list[Path], capabilities: set[str], budget: float) -> list[dict]:
    positive_number(budget, "budget")
    rows = []
    for path in paths:
        capsule = load_capsule(path)
        revisit = capsule["revisit"]
        overlap = sorted(capabilities & set(revisit["capabilities"]))
        eligible = bool(overlap) or not capabilities
        score = revisit["impact"] * (1 + bool(capsule.get("failures"))) / revisit["estimated_usd"]
        rows.append({"id": capsule["id"], "path": str(path), "title": capsule["title"],
                     "estimated_usd": revisit["estimated_usd"], "score": round(score, 4),
                     "matching_capabilities": overlap, "eligible": eligible})
    rows.sort(key=lambda r: (-int(r["eligible"]), -r["score"], r["id"]))
    remaining = budget
    for row in rows:
        row["selected"] = row["eligible"] and row["estimated_usd"] <= remaining + 1e-9
        row["reason"] = "within declared estimate" if row["selected"] else ("no capability match" if not row["eligible"] else "outside budget")
        if row["selected"]:
            remaining -= row["estimated_usd"]
    return rows
