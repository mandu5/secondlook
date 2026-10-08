import json
from pathlib import Path

import pytest

from secondlook import core
from secondlook.core import CapsuleError, load_capsule, write_json
from secondlook.runner import build_prompt, run


@pytest.fixture
def rebuild_capsule(capsule_file):
    data = json.loads(capsule_file.read_text())
    data.update(
        files=["index.html", "facts.json"], readonly_files=["facts.json"],
        rebuild={"brief": "Show Hello and keep a Docs link to https://example.org/docs.",
                 "source": "Independent project requirements, curated before generation", "confirmed": True},
        checks=[
            {"id": "greeting", "category": "intent", "basis": "Original greeting request",
             "assert": {"selector": 'role=heading[name="Hello"]', "visible": True}},
            {"id": "docs", "category": "preservation", "basis": "Documented navigation requirement",
             "assert": {"selector": 'role=link[name="Docs"]',
                        "attribute": {"name": "href", "value": "https://example.org/docs"}}},
        ],
    )
    root = capsule_file.parent / "app"
    (root / "index.html").write_text('<!-- PRIVATE_LEGACY -->\n<h1>Wrong</h1><a href="https://example.org/docs">Docs</a>')
    (root / "facts.json").write_text('{"public_fact":"Shared factual input"}')
    write_json(capsule_file, data)
    return capsule_file


def test_rebuild_prompt_is_source_blind_and_shares_facts_with_patches(rebuild_capsule):
    capsule = load_capsule(rebuild_capsule)
    bundle = {name: (Path(capsule["_root"]) / name).read_text() for name in capsule["files"]}
    prompt = build_prompt(capsule, bundle, "rebuild")
    assert "PRIVATE_LEGACY" not in prompt
    assert "Shared factual input" in prompt
    assert 'role=heading' not in prompt and '"checks"' not in prompt
    assert "writable_files" in prompt and "index.html" in prompt
    for phase in ("ordinary", "implement_reframe", "reframe", "rebuild"):
        assert capsule["rebuild"]["brief"] in build_prompt(capsule, bundle, phase)
    assert "PRIVATE_LEGACY" in build_prompt(capsule, bundle, "ordinary")


@pytest.mark.parametrize("changes", [
    {"readonly_files": ["missing.json"]}, {"readonly_files": ["facts.json", "facts.json"]},
    {"readonly_files": ["index.html", "facts.json"]},
    {"rebuild": {"brief": "", "source": "README", "confirmed": True}},
    {"rebuild": None},
    {"checks": [{"id": "bad", "category": "invented", "basis": "x",
                 "assert": {"selector": "body", "visible": True}}]},
    {"checks": [{"id": "bad", "category": "intent", "assert": {"selector": "body", "visible": True}}]},
])
def test_malformed_rebuild_contract_fails_at_load(rebuild_capsule, changes):
    data = json.loads(rebuild_capsule.read_text())
    data.update(changes)
    write_json(rebuild_capsule, data)
    with pytest.raises(CapsuleError):
        load_capsule(rebuild_capsule)


@pytest.mark.parametrize("mutation", ["missing", "unconfirmed", "projected", "no_preservation"])
def test_ineligible_rebuild_fails_before_output_or_dispatch(rebuild_capsule, tmp_path, mutation):
    data = json.loads(rebuild_capsule.read_text())
    if mutation == "missing":
        data.pop("rebuild")
    elif mutation == "unconfirmed":
        data["rebuild"]["confirmed"] = False
    elif mutation == "projected":
        data["context"] = {"index.html": {"mode": "html_scripts"}}
    else:
        data["checks"] = data["checks"][:1]
    write_json(rebuild_capsule, data)
    with pytest.raises(CapsuleError, match="rebuild|Rebuild"):
        run(rebuild_capsule, tmp_path / "out", mode="compare-three")
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("files", [
    [], [{"path": "index.html", "content": "ok"}, {"path": "index.html", "content": "duplicate"}],
    [{"path": "index.html", "content": "ok"}, {"path": "facts.json", "content": "tampered"}],
    [{"path": "../escape.html", "content": "bad"}],
    [{"path": "index.html", "content": "x" * 65_537}],
    [{"path": "index.html", "content": None}],
])
def test_entire_rebuild_output_validates_before_any_write(tmp_path, files):
    root = tmp_path / "out"
    root.mkdir()
    (root / "facts.json").write_text("original")
    with pytest.raises(CapsuleError):
        core.write_rebuild(root, files, ["index.html"])
    assert sorted(p.name for p in root.iterdir()) == ["facts.json"]
    assert (root / "facts.json").read_text() == "original"


def test_rebuild_can_replace_dom_structure_while_meeting_same_contract(rebuild_capsule, tmp_path, monkeypatch):
    import secondlook.runner as runner
    calls = []

    class Provider:
        def preflight(self):
            return "test-only"

        def call(self, prompt, schema, budget, receipt):
            calls.append((prompt, budget))
            properties = schema["properties"]
            if "objective" in properties:
                payload = {"objective": "Show Hello", "assumptions_to_challenge": [], "plan": []}
            elif "files" in properties:
                assert "PRIVATE_LEGACY" not in prompt
                assert not (receipt.parent.parent / "arms" / "D" / "index.html").exists()
                assert (receipt.parent.parent / "arms" / "D" / "facts.json").is_file()
                payload = {"summary": "Fresh implementation", "files": [{"path": "index.html",
                    "content": '<main><h2>Hello</h2><a href="https://example.org/docs">Docs</a></main>'}]}
            else:
                payload = {"summary": "Fix greeting", "edits": [{"path": "index.html", "old": "Wrong", "new": "Hello"}]}
            return {"output": payload, "cost_usd": 0.01, "models": ["test-model"],
                    "usage": {"input_tokens": 10, "output_tokens": 10}, "receipt": str(receipt)}

    monkeypatch.setattr(runner, "ClaudeProvider", lambda model: Provider())
    evidence = run(rebuild_capsule, tmp_path / "out", mode="compare-three", budget=3)
    assert evidence["status"] == "completed"
    assert list(evidence["arms"]) == ["A", "B", "C", "D"]
    assert evidence["model_calls"] == 4
    assert calls[0][1] == calls[-1][1] == 1
    assert len(evidence["comparisons"]) == 6
    assert evidence["comparisons"]["A_D"]["verdict"] == "improved"
    assert evidence["comparisons"]["C_D"]["verdict"] == "no_measured_gain"
    assert evidence["source_unchanged"] is True
    assert evidence["arms"]["D"]["input_policy"] == "independent_brief_and_readonly_files"
    for name in ("A", "B", "C", "D"):
        assert (tmp_path / "out" / "arms" / name / "facts.json").read_text() == '{"public_fact":"Shared factual input"}'
    assert (tmp_path / "out" / "D.files.json").is_file()


def test_ordinary_patch_cannot_modify_readonly_fact_to_game_checks(rebuild_capsule, tmp_path, monkeypatch):
    import secondlook.runner as runner

    class Provider:
        def preflight(self):
            return "test-only"

        def call(self, prompt, schema, budget, receipt):
            return {"output": {"summary": "Tamper", "edits": [
                {"path": "index.html", "old": "Wrong", "new": "Hello"},
                {"path": "facts.json", "old": "Shared", "new": "Tampered"}]},
                "cost_usd": .01, "models": ["test-model"], "usage": {"input_tokens": 10, "output_tokens": 10}}

    monkeypatch.setattr(runner, "ClaudeProvider", lambda model: Provider())
    evidence = run(rebuild_capsule, tmp_path / "out", mode="ordinary")
    assert evidence["arms"]["B"]["status"] == "failed"
    assert "Wrong" in (tmp_path / "out" / "arms" / "B" / "index.html").read_text()
    assert "Shared" in (tmp_path / "out" / "arms" / "B" / "facts.json").read_text()
