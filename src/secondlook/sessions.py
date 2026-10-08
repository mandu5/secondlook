"""Bounded, local-only extraction of human requests from agent session logs."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .core import CapsuleError


MAX_RECORD_BYTES = 4 * 1024 * 1024
MAX_SESSION_BYTES = 512 * 1024 * 1024
MAX_REQUEST_CHARS = 32_000
WRAPPERS = ("# AGENTS.md instructions", "<environment_context>", "<INSTRUCTIONS>", "<turn_aborted>",
            "<permissions instructions>", "<system-reminder>", "<user_instructions>", "<session_context>")


def _text(content: object) -> str | None:
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return None
    if any(not isinstance(block, dict) or not isinstance(block.get("type"), str) for block in content):
        raise ValueError("Malformed message content block")
    if any(isinstance(block, dict) and block.get("type") in {"tool_result", "tool_use", "function_call_output"} for block in content):
        return None
    chunks = [block["text"] for block in content if isinstance(block, dict)
              and block.get("type") in {"text", "input_text"} and isinstance(block.get("text"), str)]
    return "\n".join(chunks) or None


def _request(record: dict) -> tuple[str, str, str | None] | None:
    if record.get("isSidechain") or record.get("isMeta") or record.get("isCompactSummary"):
        return None
    if record.get("type") == "user" and isinstance(record.get("message"), dict):
        if record["message"].get("role", "user") != "user":
            return None
        text = _text(record["message"].get("content"))
        return (text, "claude_user", record.get("uuid")) if text else None
    payload = record.get("payload")
    if not isinstance(payload, dict):
        return None
    if record.get("type") == "response_item" and payload.get("role") == "user" and payload.get("type") == "message":
        text = _text(payload.get("content"))
        return (text, "codex_message", payload.get("id")) if text else None
    if record.get("type") == "event_msg" and payload.get("type") == "user_message":
        text = payload.get("message")
        return (text, "codex_event", payload.get("id")) if isinstance(text, str) and text else None
    return None


def read_requests(path: Path) -> dict:
    path = Path(path).resolve()
    before = path.stat()
    if before.st_size > MAX_SESSION_BYTES:
        raise CapsuleError(f"Selected session exceeds {MAX_SESSION_BYTES:,} bytes")
    result = {"session_path": str(path), "session_id": path.stem, "requests": [], "recorded_model_hints": [],
              "skipped": {"malformed": 0, "oversized": 0, "wrappers": 0, "duplicates": 0}}
    digest = hashlib.sha256()
    total = line_number = 0
    seen_ids, models = set(), set()
    with path.open("rb") as stream:
        while True:
            raw = stream.readline(MAX_RECORD_BYTES + 1)
            if not raw:
                break
            line_number += 1
            total += len(raw)
            digest.update(raw)
            if total > MAX_SESSION_BYTES:
                raise CapsuleError("Selected session exceeded size limit while reading")
            if len(raw) > MAX_RECORD_BYTES:
                result["skipped"]["oversized"] += 1
                while raw and not raw.endswith(b"\n"):
                    raw = stream.readline(MAX_RECORD_BYTES + 1)
                    total += len(raw)
                    digest.update(raw)
                    if total > MAX_SESSION_BYTES:
                        raise CapsuleError("Selected session exceeded size limit while reading")
                continue
            try:
                record = json.loads(raw)
                if not isinstance(record, dict):
                    raise ValueError("Expected object")
                # JSON escapes can decode to lone surrogates even when the raw
                # line is UTF-8. Reject them in provenance/model metadata too.
                json.dumps(record, ensure_ascii=False, allow_nan=False).encode("utf-8")
            except (ValueError, UnicodeError, RecursionError):
                result["skipped"]["malformed"] += 1
                continue
            payload = record.get("payload")
            if record.get("type") == "session_meta" and isinstance(payload, dict):
                result["session_id"] = payload.get("id") or payload.get("session_id") or path.stem
            if record.get("type") == "turn_context" and isinstance(payload, dict) and isinstance(payload.get("model"), str):
                models.add(payload["model"])
            message = record.get("message")
            if record.get("type") == "assistant" and isinstance(message, dict) and isinstance(message.get("model"), str):
                if message["model"] not in {"<synthetic>", "unknown"}:
                    models.add(message["model"])
            try:
                found = _request(record)
                if found is not None:
                    encoded_text = found[0].encode("utf-8")
            except (ValueError, UnicodeError):
                result["skipped"]["malformed"] += 1
                continue
            if found is None:
                continue
            text, kind, request_id = found
            if text.lstrip().startswith(WRAPPERS):
                result["skipped"]["wrappers"] += 1
                continue
            if len(text) > MAX_REQUEST_CHARS:
                result["skipped"]["oversized"] += 1
                continue
            if isinstance(request_id, str) and request_id in seen_ids:
                result["skipped"]["duplicates"] += 1
                continue
            # Some Codex versions emit both a message and a neighboring event.
            previous = result["requests"][-1] if result["requests"] else None
            if previous and {previous["kind"], kind} == {"codex_message", "codex_event"} and previous["text"] == text and line_number - previous["line"] <= 5:
                result["skipped"]["duplicates"] += 1
                continue
            if isinstance(request_id, str):
                seen_ids.add(request_id)
            result["requests"].append({"line": line_number, "text": text, "kind": kind, "request_id": request_id,
                                       "record_sha256": hashlib.sha256(raw).hexdigest(),
                                       "text_sha256": hashlib.sha256(encoded_text).hexdigest()})
    after = path.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise CapsuleError("Session changed during capture; select a stable exported log")
    result["session_sha256"] = digest.hexdigest()
    result["recorded_model_hints"] = sorted(models)
    result["note"] = "Model hints describe this session, not verified authorship of the artifact. No tool output was imported."
    return result


def select_request(session: dict, line: int) -> dict:
    for request in session["requests"]:
        if request["line"] == line:
            return {**request, "session_path": session["session_path"], "session_id": session["session_id"],
                    "session_sha256": session["session_sha256"], "recorded_model_hints": session["recorded_model_hints"]}
    raise CapsuleError(f"Line {line} is not an eligible human request; inspect 'secondlook requests' output")
