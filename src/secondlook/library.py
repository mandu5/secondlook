"""Versioned, local problem records and a durable revisit journal."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import json
import gzip
import hashlib
import os
from pathlib import Path
import re
import sqlite3
import tempfile
import zlib
from uuid import uuid4

from .artifacts import MAX_RUNTIME_BYTES, artifact_from_sources, capture_artifact
from .catalog import normalize_catalog
from .core import CapsuleError, fingerprint, load_capsule, positive_number, public_capsule, write_bundle, write_json


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def dumps(value: object) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)
    except (ValueError, TypeError) as error:
        raise CapsuleError("Record must contain finite JSON values") from error


def label(value: object, name: str, maximum: int = 32000) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise CapsuleError(f"{name} must be nonempty text (at most {maximum} characters)")
    try:
        value.encode("utf-8")
    except UnicodeError as error:
        raise CapsuleError(f"{name} must be valid UTF-8") from error
    return value


def identifier(value: object) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,80}", value):
        raise CapsuleError("ID must use 1 through 80 letters, numbers, hyphens or underscores")
    return value


def tags(value: object) -> list[str]:
    if not isinstance(value, list) or not 1 <= len(value) <= 40:
        raise CapsuleError("Declare 1 through 40 capability tags")
    return sorted({label(item, "capability", 80).strip().lower() for item in value})


def validate_problem(data: dict) -> dict:
    if not isinstance(data, dict):
        raise CapsuleError("Problem record must be an object")
    identifier(data.get("id"))
    label(data.get("title"), "title", 240)
    label(data.get("kind"), "kind", 80)
    intent = data.get("intent")
    if not isinstance(intent, dict) or type(intent.get("confirmed")) is not bool:
        raise CapsuleError("Intent needs an explicit confirmed boolean")
    label(intent.get("text"), "original intent")
    label(intent.get("source"), "intent source", 4000)
    for key in ("constraints", "failures"):
        values = data.get(key, [])
        if not isinstance(values, list) or len(values) > 100:
            raise CapsuleError(f"{key} must be a bounded list")
        for item in values:
            label(item, key, 4000)
    assumptions = data.get("assumptions", [])
    if not isinstance(assumptions, list) or len(assumptions) > 100:
        raise CapsuleError("assumptions must be a bounded list with provenance")
    revisit = data.get("revisit")
    if not isinstance(revisit, dict):
        raise CapsuleError("Declare revisit capabilities, impact and estimated_usd")
    capabilities = tags(revisit.get("capabilities"))
    cost = positive_number(revisit.get("estimated_usd"), "estimated_usd")
    impact = positive_number(revisit.get("impact"), "impact")
    if impact > 5:
        raise CapsuleError("impact must be 1 through 5")
    result = {key: data[key] for key in ("id", "title", "kind", "intent")}
    result.update(constraints=data.get("constraints", []), failures=data.get("failures", []), assumptions=assumptions,
                  revisit={"capabilities": capabilities, "impact": impact, "estimated_usd": cost})
    return result


class Library:
    def __init__(self, path: Path):
        self.path = Path(path).resolve()
        self.path.mkdir(parents=True, exist_ok=True)
        self.db_path = self.path / "library.sqlite3"
        with self.transaction() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS versions (
                    kind TEXT, id TEXT, revision TEXT, body TEXT NOT NULL, created TEXT NOT NULL,
                    PRIMARY KEY (kind,id,revision));
                CREATE TABLE IF NOT EXISTS heads (kind TEXT,id TEXT,revision TEXT,PRIMARY KEY(kind,id));
                CREATE TABLE IF NOT EXISTS catalogs (source TEXT PRIMARY KEY,body TEXT NOT NULL,observed TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS events (id TEXT PRIMARY KEY,body TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS plans (id TEXT PRIMARY KEY,body TEXT NOT NULL,status TEXT NOT NULL,result TEXT);
                CREATE TABLE IF NOT EXISTS attempts (
                    key TEXT PRIMARY KEY,plan_id TEXT NOT NULL,task_id TEXT NOT NULL,status TEXT NOT NULL,
                    output TEXT NOT NULL,summary TEXT);
            """)

    @contextmanager
    def transaction(self):
        db = sqlite3.connect(self.db_path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def put(self, kind: str, key: str, body: dict) -> dict:
        text = dumps(body)
        if len(text.encode("utf-8")) > 2 * 1024 * 1024:
            raise CapsuleError("Problem/profile record exceeds 2 MiB")
        revision = fingerprint(body)
        with self.transaction() as db:
            db.execute("INSERT OR IGNORE INTO versions VALUES(?,?,?,?,?)", (kind, key, revision, text, now()))
            db.execute("INSERT INTO heads VALUES(?,?,?) ON CONFLICT(kind,id) DO UPDATE SET revision=excluded.revision",
                       (kind, key, revision))
        return {**body, "revision": revision}

    def get(self, kind: str, key: str, revision: str | None = None) -> dict:
        with self.transaction() as db:
            if revision is None:
                head = db.execute("SELECT revision FROM heads WHERE kind=? AND id=?", (kind, key)).fetchone()
                revision = head[0] if head else None
            row = db.execute("SELECT body FROM versions WHERE kind=? AND id=? AND revision=?", (kind, key, revision)).fetchone()
        if row is None:
            raise CapsuleError(f"Unknown {kind}: {key}")
        return {**json.loads(row[0]), "revision": revision}

    def list(self, kind: str) -> list[dict]:
        with self.transaction() as db:
            rows = db.execute("SELECT v.body,v.revision FROM versions v JOIN heads h USING(kind,id,revision) WHERE kind=? ORDER BY v.id", (kind,)).fetchall()
        return [{**json.loads(row[0]), "revision": row[1]} for row in rows]

    def records(self) -> list[dict]:
        return self.list("task")

    def harvest_problem(self, data: dict) -> dict:
        body = validate_problem(data)
        body["adapter"] = None
        return self.put("task", body["id"], body)

    def harvest_capsule(self, path: Path) -> dict:
        capsule = load_capsule(path)
        artifact = capture_artifact(capsule)
        data = {**public_capsule(capsule), "kind": "static-app"}
        body = validate_problem(data)
        frozen = public_capsule(capsule)
        frozen["root"] = capsule["_root"]
        snapshot = {}
        objects = self.path / "objects"
        objects.mkdir(exist_ok=True)
        for name, source in artifact.sources.items():
            raw = source.encode("utf-8")
            digest = hashlib.sha256(raw).hexdigest()
            target = objects / (digest + ".gz")
            if not target.exists():
                fd, temporary = tempfile.mkstemp(dir=objects, prefix=".snapshot-")
                try:
                    with os.fdopen(fd, "wb") as stream:
                        with gzip.GzipFile(filename="", mode="wb", fileobj=stream, mtime=0) as compressed:
                            compressed.write(raw)
                        stream.flush()
                        os.fsync(stream.fileno())
                    os.replace(temporary, target)
                finally:
                    if os.path.exists(temporary):
                        os.unlink(temporary)
            if self._blob(digest, MAX_RUNTIME_BYTES) != raw:
                raise CapsuleError("Snapshot object is corrupt; original history was not replaced")
            snapshot[name] = digest
        body.update(adapter="static-html", capsule=frozen, capsule_path=str(Path(path).resolve()),
                    source_identity=artifact.identity, source_metrics=artifact.metrics, snapshot=snapshot)
        return self.put("task", body["id"], body)

    def _blob(self, digest: str, maximum: int) -> bytes:
        if not isinstance(digest, str) or not re.fullmatch(r"[a-f0-9]{64}", digest):
            raise CapsuleError("Invalid snapshot object identity")
        path = self.path / "objects" / (digest + ".gz")
        try:
            if path.is_symlink():
                raise CapsuleError("Snapshot objects cannot be symlinks")
            with gzip.open(path, "rb") as stream:
                raw = stream.read(maximum + 1)
        except (OSError, EOFError, zlib.error) as error:
            raise CapsuleError("Snapshot object is missing or corrupt") from error
        if len(raw) > maximum or hashlib.sha256(raw).hexdigest() != digest:
            raise CapsuleError("Snapshot content does not match its recorded identity")
        return raw

    def restore(self, task_id: str, destination: Path, revision: str | None = None) -> Path:
        record = self.get("task", task_id, revision)
        destination = Path(destination).resolve()
        if destination.exists():
            raise CapsuleError("Restore destination must not exist")
        snapshot = record.get("snapshot")
        if not isinstance(snapshot, dict) or set(snapshot) != set(record["capsule"]["files"]):
            raise CapsuleError("This revision has no complete source snapshot; older metadata-only records need re-harvesting")
        if destination.is_relative_to(Path(record["capsule"]["root"])):
            raise CapsuleError("Restore outside the original source root")
        sources, used = {}, 0
        for name, digest in snapshot.items():
            raw = self._blob(digest, MAX_RUNTIME_BYTES - used)
            used += len(raw)
            try:
                sources[name] = raw.decode("utf-8")
            except UnicodeError as error:
                raise CapsuleError("Snapshot is not UTF-8") from error
        artifact = artifact_from_sources(sources, record["capsule"].get("context"))
        if artifact.identity != record["source_identity"]:
            raise CapsuleError("Snapshot does not match the harvested revision")
        destination.mkdir(parents=True)
        write_bundle(destination / "source", sources)
        capsule = {**record["capsule"], "root": "source"}
        path = destination / "capsule.json"
        write_json(path, capsule)
        return path

    def register_candidate(self, profile: dict) -> dict:
        if not isinstance(profile, dict):
            raise CapsuleError("Candidate profile must be an object")
        key = identifier(profile.get("id"))
        if profile.get("provider") != "claude-cli":
            raise CapsuleError("Only the claude-cli execution provider is implemented")
        runtime = label(profile.get("runtime_model"), "runtime_model", 160)
        if not re.fullmatch(r"claude-[a-zA-Z0-9][a-zA-Z0-9._-]+", runtime):
            raise CapsuleError("Use an explicit Claude model ID, not an alias such as sonnet")
        body = {"id": key, "provider": "claude-cli", "runtime_model": runtime,
                "declared_revision": label(profile.get("revision"), "candidate revision", 160),
                "capabilities": tags(profile.get("capabilities")),
                "evidence": label(profile.get("evidence"), "capability evidence", 4000)}
        if profile.get("catalog_id") is not None:
            body["catalog_id"] = label(profile["catalog_id"], "catalog_id", 240)
            body["catalog_source"] = label(profile.get("catalog_source"), "catalog_source", 2000)
        return self.put("candidate", key, body)

    def candidate(self, key: str) -> dict:
        return self.get("candidate", key)

    def sync_catalog(self, payload: object, source: str) -> dict:
        source = label(source, "catalog source", 2000)
        models = normalize_catalog(payload)
        stamp, events = now(), []
        with self.transaction() as db:
            previous = db.execute("SELECT body FROM catalogs WHERE source=?", (source,)).fetchone()
            if previous:
                old = json.loads(previous[0])
                for key in sorted(set(old) | set(models)):
                    before, after = old.get(key), models.get(key)
                    if before == after:
                        continue
                    event = {"id": uuid4().hex, "source": source, "model_id": key, "observed_at": stamp,
                             "kind": "added" if before is None else "removed" if after is None else "changed",
                             "before": before, "after": after, "quality_improvement": "not established"}
                    db.execute("INSERT INTO events VALUES(?,?)", (event["id"], dumps(event)))
                    events.append(event)
            db.execute("INSERT INTO catalogs VALUES(?,?,?) ON CONFLICT(source) DO UPDATE SET body=excluded.body,observed=excluded.observed",
                       (source, dumps(models), stamp))
        return {"baseline": previous is None, "source": source, "observed_at": stamp,
                "model_count": len(models), "fingerprint": fingerprint(models), "events": events, "model_calls": 0}
