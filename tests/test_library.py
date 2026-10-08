import copy
import json

import pytest

from secondlook.core import CapsuleError
from secondlook.fixtures import create_demo
from secondlook.library import Library


def problem(task_id="research"):
    return {"id": task_id, "title": "Explain a disputed research claim", "kind": "research",
            "intent": {"text": "Find independently checkable evidence", "source": "Owner note", "confirmed": True},
            "constraints": ["Cite primary sources"], "failures": ["Evidence remains incomplete"],
            "assumptions": [{"text": "A longer context may help", "source": "Old assistant hypothesis"}],
            "revisit": {"capabilities": ["research"], "impact": 4, "estimated_usd": 0.5}}


def profile(candidate_id="candidate"):
    return {"id": candidate_id, "runtime_model": "claude-test-version", "revision": "test-1",
            "provider": "claude-cli", "capabilities": ["coding"],
            "evidence": "Test fixture: capability claim, not measured uplift"}


def catalog(*ids):
    return {"data": [{"id": key, "name": key, "created": 100, "context_length": 10000,
                      "architecture": {"input_modalities": ["text"], "output_modalities": ["text"]},
                      "supported_parameters": ["tools"], "pricing": {"prompt": "0.000001", "completion": "0.000002"}}
                     for key in ids]}


def test_harvest_retains_revisions_and_does_not_invent_authorship(tmp_path):
    lib = Library(tmp_path / "library")
    path = create_demo(tmp_path / "demo")
    first = lib.harvest_capsule(path)
    again = lib.harvest_capsule(path)
    assert first["revision"] == again["revision"]
    source = path.parent / "app" / "index.html"
    # The fixture stores the actual root in its capsule.
    raw = json.loads(path.read_text())
    source = (path.parent / raw["root"] / "index.html").resolve()
    source.write_text(source.read_text() + "\n<!-- new source -->")
    changed = lib.harvest_capsule(path)
    assert changed["revision"] != first["revision"]
    assert len(lib.records()) == 1
    assert lib.get("task", first["id"], first["revision"])["source_identity"] == first["source_identity"]
    assert changed["capsule"]["baseline"] == raw["baseline"]


def test_generic_problem_keeps_intent_assumptions_and_has_no_execution_adapter(tmp_path):
    lib = Library(tmp_path / "library")
    saved = lib.harvest_problem(problem())
    assert saved["adapter"] is None
    assert saved["intent"]["text"] == "Find independently checkable evidence"
    assert saved["assumptions"][0]["source"] == "Old assistant hypothesis"
    assert Library(lib.path).records()[0]["revision"] == saved["revision"]


def test_catalog_first_sync_is_inventory_later_changes_are_observations(tmp_path):
    lib = Library(tmp_path / "library")
    first = lib.sync_catalog(catalog("vendor/old"), "fixture:catalog")
    assert first["baseline"] is True and first["events"] == []
    second = lib.sync_catalog(catalog("vendor/new"), "fixture:catalog")
    assert {(e["model_id"], e["kind"]) for e in second["events"]} == {
        ("vendor/old", "removed"), ("vendor/new", "added")}
    assert lib.sync_catalog(catalog("vendor/new"), "fixture:catalog")["events"] == []
    invalid = catalog("vendor/new", "vendor/new")
    with pytest.raises(CapsuleError):
        lib.sync_catalog(invalid, "fixture:catalog")
    assert lib.sync_catalog(catalog("vendor/new"), "fixture:catalog")["events"] == []


@pytest.mark.parametrize("mutate", [
    lambda p: p.update(runtime_model="sonnet"),
    lambda p: p.update(revision=""),
    lambda p: p.update(capabilities=[]),
    lambda p: p.update(evidence=""),
    lambda p: p.update(provider="unknown"),
])
def test_ambiguous_candidate_configuration_is_rejected(tmp_path, mutate):
    data = copy.deepcopy(profile())
    mutate(data)
    with pytest.raises(CapsuleError):
        Library(tmp_path).register_candidate(data)


@pytest.mark.parametrize("bad", [True, float("nan"), -1, 0])
def test_problem_cost_must_be_a_finite_positive_number(tmp_path, bad):
    data = problem()
    data["revisit"]["estimated_usd"] = bad
    with pytest.raises(CapsuleError):
        Library(tmp_path).harvest_problem(data)


def test_live_catalog_tiered_prices_are_preserved_and_malformed_tiers_are_atomic(tmp_path):
    lib = Library(tmp_path)
    data = catalog("vendor/tiered")
    data["data"][0]["pricing"]["overrides"] = [
        {"min_prompt_tokens": 200000, "prompt": "0.000006", "completion": "0.0000225"},
        {"utc_days": ["saturday", "sunday"], "utc_start": 0, "utc_end": 100, "prompt": "0.000003"}]
    assert lib.sync_catalog(data, "fixture:tiers")["model_count"] == 1
    changed = copy.deepcopy(data)
    changed["data"][0]["pricing"]["overrides"][0]["prompt"] = "not-a-price"
    with pytest.raises(CapsuleError):
        lib.sync_catalog(changed, "fixture:tiers")
    assert lib.sync_catalog(data, "fixture:tiers")["events"] == []


def test_original_artifact_can_be_restored_after_source_deletion(tmp_path):
    lib = Library(tmp_path / "library")
    path = create_demo(tmp_path / "demo")
    original = (path.parent / "index.html").read_bytes()
    record = lib.harvest_capsule(path)
    (path.parent / "index.html").unlink()
    restored = lib.restore(record["id"], tmp_path / "restored", record["revision"])
    assert (restored.parent / "source" / "index.html").read_bytes() == original
    with pytest.raises(CapsuleError):
        lib.restore(record["id"], tmp_path / "restored", record["revision"])


def test_corrupt_snapshot_cannot_be_restored_or_replace_original_history(tmp_path):
    lib = Library(tmp_path / "library")
    record = lib.harvest_capsule(create_demo(tmp_path / "demo"))
    blob = next((lib.path / "objects").glob("*.gz"))
    blob.write_bytes(b"corrupted")
    with pytest.raises(CapsuleError):
        lib.restore(record["id"], tmp_path / "restored")
    assert not (tmp_path / "restored").exists()
