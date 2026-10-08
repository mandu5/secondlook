import json

import pytest

from secondlook.core import CapsuleError, apply_edits, fingerprint, load_capsule, plan_capsules, source_bundle


def change(path, **fields):
    value = json.loads(path.read_text())
    value.update(fields)
    path.write_text(json.dumps(value))


def test_snapshot_is_explicit_and_fingerprint_tracks_changes(capsule_file):
    capsule = load_capsule(capsule_file)
    first = source_bundle(capsule)
    assert first == {"index.html": '<h1 id="title">Hello</h1>'}
    (capsule_file.parent / "app" / ".env").write_text("SECRET=never-read")
    assert source_bundle(capsule) == first
    (capsule_file.parent / "app" / "index.html").write_text("changed")
    assert fingerprint(source_bundle(capsule)) != fingerprint(first)
    assert fingerprint({"a": 1, "b": 2}) == fingerprint({"b": 2, "a": 1})


@pytest.mark.parametrize("path", ["../private.txt", "/etc/passwd", ".env", "nested/.git/config", "C:\\secret", "id_rsa", "secret.pem"])
def test_unsafe_source_paths_rejected(capsule_file, path):
    change(capsule_file, files=[path], entrypoint=path)
    with pytest.raises(CapsuleError):
        source_bundle(load_capsule(capsule_file))


def test_symlink_and_oversized_context_rejected(capsule_file):
    index = capsule_file.parent / "app" / "index.html"
    index.unlink()
    index.symlink_to(capsule_file)
    with pytest.raises(CapsuleError, match="symlink"):
        source_bundle(load_capsule(capsule_file))
    index.unlink()
    index.write_text("x" * 70000)
    with pytest.raises(CapsuleError, match="context"):
        source_bundle(load_capsule(capsule_file))


def test_patch_validation_does_not_partially_write(capsule_file):
    root = capsule_file.parent / "app"
    original = (root / "index.html").read_text()
    with pytest.raises(CapsuleError):
        apply_edits(root, [
            {"path": "index.html", "old": "Hello", "new": "Better"},
            {"path": "../capsule.json", "old": "x", "new": "oops"},
        ], ["index.html"])
    assert (root / "index.html").read_text() == original
    apply_edits(root, [{"path": "index.html", "old": "Hello", "new": "Better"}], ["index.html"])
    assert "Better" in (root / "index.html").read_text()


def test_ambiguous_anchor_refused(capsule_file):
    root = capsule_file.parent / "app"
    (root / "index.html").write_text("same same")
    with pytest.raises(CapsuleError, match="exactly once"):
        apply_edits(root, [{"path": "index.html", "old": "same", "new": "new"}], ["index.html"])


def test_plan_obeys_budget_and_capability_trigger(capsule_file):
    other = capsule_file.with_name("other.json")
    other.write_text(capsule_file.read_text())
    change(other, id="other", revisit={"capabilities": ["vision"], "impact": 5, "estimated_usd": 0.2})
    rows = plan_capsules([capsule_file, other], {"coding"}, 0.5)
    assert [r["id"] for r in rows if r["selected"]] == ["hello"]
    assert sum(r["estimated_usd"] for r in rows if r["selected"]) <= 0.5
    assert not any(r["selected"] for r in plan_capsules([capsule_file], {"coding"}, 0.1))


@pytest.mark.parametrize("bad", [float("nan"), -1, True, 0])
def test_invalid_budget_estimate_rejected(capsule_file, bad):
    change(capsule_file, revisit={"capabilities": [], "impact": 3, "estimated_usd": bad})
    with pytest.raises(CapsuleError):
        load_capsule(capsule_file)


def test_checks_need_unique_ids_and_nonempty_assertions(capsule_file):
    change(capsule_file, checks=[{"id": "x", "assert": {}}, {"id": "x", "assert": {}}])
    with pytest.raises(CapsuleError):
        load_capsule(capsule_file)


@pytest.mark.parametrize("assertion,actions", [
    ({"csv": None}, []),
    ({"csv": [["id"]]}, []),
    ({"csv": [[1]]}, [{"type": "download", "selector": "#export"}]),
    ({"selector": "h1", "count": "1"}, []),
    ({"selector": "h1", "count": True}, []),
    ({"selector": "h1", "count": -1}, []),
    ({"selector": "h1", "visible": "false"}, []),
    ({"selector": "h1", "text": None}, []),
    ({"selector": "input", "value": 7}, []),
    ({"selector": "", "visible": True}, []),
    ({"csv": [], "selector": "h1", "visible": True}, [{"type": "download", "selector": "#export"}]),
])
def test_malformed_checks_rejected_before_evaluation(capsule_file, assertion, actions):
    change(capsule_file, checks=[{"id": "bad-check", "assert": assertion, "actions": actions}])
    with pytest.raises(CapsuleError):
        load_capsule(capsule_file)
