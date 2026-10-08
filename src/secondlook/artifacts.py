"""Complete local runtime snapshots with explicit, bounded model projections."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from html.parser import HTMLParser
from pathlib import Path
import re

from .core import CapsuleError, MAX_CONTEXT_BYTES, fingerprint, source_path


MAX_RUNTIME_BYTES = 256 * 1024 * 1024
SCRIPT_TYPES = {"", "module", "text/javascript", "application/javascript", "text/ecmascript", "application/ecmascript"}


class _Scripts(HTMLParser):
    # Scripting is enabled in the evaluator. These elements' contents are text,
    # including noscript and the RCDATA title/textarea elements (no nested tags).
    CDATA_CONTENT_ELEMENTS = ("script", "style", "textarea", "title", "noscript", "xmp", "iframe", "noembed", "noframes")
    UNSUPPORTED = {"plaintext", "template", "svg", "math"}

    def __init__(self, source: str):
        super().__init__(convert_charrefs=False)
        self.source = source
        self.lines = [0] + [match.end() for match in re.finditer("\n", source)]
        self.active: int | None = None
        self.spans: list[tuple[int, int]] = []

    def source_position(self) -> int:
        line, column = self.getpos()
        return self.lines[line - 1] + column

    def handle_starttag(self, tag, attrs):
        if tag in self.UNSUPPORTED:
            raise CapsuleError(f"HTML script projection does not support {tag}; select explicit source files instead")
        if tag in self.CDATA_CONTENT_ELEMENTS and not re.match(r"<" + tag + r"(?=[\t\n\f\r />])", self.get_starttag_text(), re.I):
            raise CapsuleError("Ambiguous raw-text opening tag in HTML script projection")
        if tag != "script":
            return
        attributes = {}
        for name, value in attrs:
            attributes.setdefault(name, value)  # HTML keeps the first duplicate.
        kind = (attributes.get("type") or "").strip("\t\n\f\r ").lower()
        if "src" not in attributes and "nomodule" not in attributes and kind in SCRIPT_TYPES:
            self.active = self.source_position() + len(self.get_starttag_text())

    def handle_startendtag(self, tag, attrs):
        if tag in self.CDATA_CONTENT_ELEMENTS or tag in self.UNSUPPORTED:
            raise CapsuleError("Self-closing raw-text/foreign tags are ambiguous in HTML script projection")
        super().handle_startendtag(tag, attrs)

    def handle_data(self, data):
        # HTMLParser does not implement HTML's script escape/double-escape states
        # or malformed raw-text end tags. Refuse these instead of guessing.
        if self.cdata_elem == "script" and re.search(r"<!--|</script(?=[\t\n\f\r />])", data, re.I):
            raise CapsuleError("Unsupported script escape or closing-tag syntax in HTML projection")

    def handle_endtag(self, tag):
        if self.cdata_elem is not None:
            start = self.source_position()
            end = self.source.find(">", start) + 1
            if not re.fullmatch(r"</" + re.escape(tag) + r"[\t\n\f\r ]*>", self.source[start:end], re.I):
                raise CapsuleError("Ambiguous raw-text closing tag in HTML script projection")
        if tag == "script" and self.active is not None:
            end = self.source_position()
            if self.source[self.active:end].strip():
                self.spans.append((self.active, end))
            self.active = None


def validate_context(context: object, files: list[str]) -> dict:
    if context is None:
        return {}
    if not isinstance(context, dict) or set(context) - set(files):
        raise CapsuleError("Context policies must refer only to allowlisted files")
    for name, policy in context.items():
        if not isinstance(policy, dict) or policy != {"mode": "html_scripts"}:
            raise CapsuleError("Supported context policy is exactly {mode: html_scripts}")
        if Path(name).suffix.lower() not in {".html", ".htm"}:
            raise CapsuleError("html_scripts projection requires an HTML file")
    return context


def context_spans(text: str, policy: dict | None) -> list[tuple[int, int]]:
    if policy is None:
        return [(0, len(text))]
    if policy != {"mode": "html_scripts"}:
        raise CapsuleError("Unsupported context projection")
    parser = _Scripts(text)
    parser.feed(text)
    parser.close()
    if parser.active is not None:
        raise CapsuleError("Selected script has no closing tag")
    if not parser.spans:
        raise CapsuleError("No executable inline script selected; external/data scripts are read-only")
    return parser.spans


def project_text(text: str, policy: dict | None) -> str:
    spans = context_spans(text, policy)
    if policy is None:
        return text
    return "\n\n".join(f"/* Selected inline script {i + 1}; boundary marker is not part of the file. */\n" + text[start:end]
                        for i, (start, end) in enumerate(spans))


@dataclass(frozen=True)
class Artifact:
    sources: dict[str, str]
    context: dict[str, str]
    identity: str
    metrics: dict


def artifact_from_sources(sources: dict[str, str], context: dict | None = None) -> Artifact:
    policies = validate_context(context, list(sources))
    projected = {}
    files = {}
    runtime_bytes = context_bytes = 0
    for name, text in sources.items():
        raw = text.encode("utf-8")
        runtime_bytes += len(raw)
        if runtime_bytes > MAX_RUNTIME_BYTES:
            raise CapsuleError(f"Allowlisted runtime source exceeds {MAX_RUNTIME_BYTES:,} bytes")
        selected = project_text(text, policies.get(name))
        size = len(selected.encode("utf-8"))
        context_bytes += size
        if context_bytes > MAX_CONTEXT_BYTES:
            raise CapsuleError(f"Source context exceeds {MAX_CONTEXT_BYTES:,} bytes; select executable scripts or fewer files")
        projected[name] = selected
        files[name] = {"sha256": hashlib.sha256(raw).hexdigest(), "runtime_bytes": len(raw), "context_bytes": size,
                       "projection": policies.get(name, {"mode": "full"}), "selected_regions": len(context_spans(text, policies.get(name)))}
    identity = fingerprint({"method": "file-bytes-and-projection-v1", "files": files})
    return Artifact(sources, projected, identity, {"runtime_bytes": runtime_bytes, "context_bytes": context_bytes,
                    "excluded_bytes": max(0, runtime_bytes - context_bytes), "files": files,
                    "note": "UTF-8 source bytes excluded from context, not measured token savings. Prompt overhead is additional."})


def capture_artifact(capsule: dict) -> Artifact:
    policies = validate_context(capsule.get("context"), capsule["files"])
    sources = {}
    runtime_bytes = full_context_bytes = 0
    for name in capsule["files"]:
        path = source_path(Path(capsule["_root"]), name)
        try:
            size = path.stat().st_size
            runtime_bytes += size
            if runtime_bytes > MAX_RUNTIME_BYTES:
                raise CapsuleError(f"Allowlisted runtime source exceeds {MAX_RUNTIME_BYTES:,} bytes")
            if name not in policies:
                full_context_bytes += size
                if full_context_bytes > MAX_CONTEXT_BYTES:
                    raise CapsuleError(f"Source context exceeds {MAX_CONTEXT_BYTES:,} bytes; use an explicit projection")
            with path.open("rb") as stream:
                raw = stream.read(size + 1)
            if len(raw) != size:
                raise CapsuleError(f"Source changed during snapshot: {name}")
            sources[name] = raw.decode("utf-8")
        except (OSError, UnicodeError) as error:
            raise CapsuleError(f"Cannot read UTF-8 source {name}: {error}") from error
    return artifact_from_sources(sources, policies)
