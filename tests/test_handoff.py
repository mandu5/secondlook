import json
from pathlib import Path
import shutil

import pytest

from secondlook.core import CapsuleError


def rebuild_capsule(path):
    data = json.loads(path.read_text())
    data["rebuild"] = {"brief": "Show a Hello heading and keep the footer.",
                       "source": "Owner requirements", "confirmed": True}
    data["checks"] = [
        {"id": "purpose", "category": "intent", "basis": "Owner", "assert": {"selector": "h1", "text": "Hello"}},
        {"id": "keep", "category": "preservation", "basis": "Owner", "assert": {"selector": "footer", "text": "Saved"}},
    ]
    path.write_text(json.dumps(data))


def test_rebuild_request_is_source_blind_and_portable(capsule_file, tmp_path):
    from secondlook.handoff import load_request, prepare_request
    rebuild_capsule(capsule_file)
    source = capsule_file.parent / "app" / "index.html"
    source.write_text('<h1>LEGACY_SECRET</h1><footer>Saved</footer>')
    prepared = prepare_request(capsule_file, tmp_path / "request")
    prompt = (tmp_path / "request" / "request.md").read_text()
    assert "LEGACY_SECRET" not in prompt
    assert '"selector"' not in prompt
    assert 'Show a Hello heading' in prompt
    assert prepared["request_id"] in prompt
    schema = json.loads((tmp_path / "request" / "response.schema.json").read_text())
    assert schema["properties"]["request_id"]["const"] == prepared["request_id"]
    shutil.move(tmp_path / "request", tmp_path / "moved")
    shutil.rmtree(source.parent)
    manifest, capsule, artifact = load_request(tmp_path / "moved")
    assert manifest["request_id"] == prepared["request_id"]
    assert artifact.sources["index.html"] == '<h1>LEGACY_SECRET</h1><footer>Saved</footer>'
    assert Path(capsule["_root"]) == tmp_path / "moved" / "baseline"


def test_ordinary_request_includes_selected_source_but_not_checks(capsule_file, tmp_path):
    from secondlook.handoff import prepare_request
    source = capsule_file.parent / "app" / "index.html"
    source.write_text('<h1>PRIVATE_CSS_CONTENT</h1><script>const answer=41;</script>')
    data = json.loads(capsule_file.read_text())
    data["context"] = {"index.html": {"mode": "html_scripts"}}
    capsule_file.write_text(json.dumps(data))
    prepare_request(capsule_file, tmp_path / "request", mode="ordinary")
    prompt = (tmp_path / "request" / "request.md").read_text()
    assert "const answer=41" in prompt
    assert "PRIVATE_CSS_CONTENT" not in prompt
    assert '"selector"' not in prompt


@pytest.mark.parametrize("target", ["baseline/index.html", "capsule.frozen.json", "request.md", "response.schema.json"])
def test_modified_request_is_rejected(capsule_file, tmp_path, target):
    from secondlook.handoff import load_request, prepare_request
    folder = tmp_path / "request"
    prepare_request(capsule_file, folder, mode="ordinary")
    path = folder / target
    path.write_text(path.read_text().replace("Hello", "Changed") if "Hello" in path.read_text() else path.read_text() + " ")
    with pytest.raises(CapsuleError, match="changed|identity|modified"):
        load_request(folder)


@pytest.mark.parametrize("target", ["baseline", "capsule.frozen.json", "request.json", "request.md"])
def test_request_symlinks_are_rejected(capsule_file, tmp_path, target):
    from secondlook.handoff import load_request, prepare_request
    folder = tmp_path / "request"
    prepare_request(capsule_file, folder, mode="ordinary")
    path = folder / target
    saved = tmp_path / "elsewhere"
    shutil.move(path, saved)
    path.symlink_to(saved, target_is_directory=saved.is_dir())
    with pytest.raises(CapsuleError, match="symlink"):
        load_request(folder)


def test_request_requires_confirmation_and_independent_rebuild_contract(capsule_file, tmp_path):
    from secondlook.handoff import prepare_request
    with pytest.raises(CapsuleError, match="rebuild|independent"):
        prepare_request(capsule_file, tmp_path / "rebuild")
    data = json.loads(capsule_file.read_text())
    data["intent"]["confirmed"] = False
    capsule_file.write_text(json.dumps(data))
    with pytest.raises(CapsuleError, match="Confirm|confirmed"):
        prepare_request(capsule_file, tmp_path / "draft", mode="ordinary")
    assert not (tmp_path / "draft").exists()


def test_request_output_cannot_overwrite_or_live_inside_source(capsule_file, tmp_path):
    from secondlook.handoff import prepare_request
    with pytest.raises(CapsuleError, match="outside|source"):
        prepare_request(capsule_file, tmp_path / "app" / "request", mode="ordinary")
    with pytest.raises(CapsuleError, match="new|exists"):
        prepare_request(capsule_file, tmp_path, mode="ordinary")


@pytest.mark.parametrize("raw", ['{"a": 1, "a": 2}', '{"a": NaN}', '{"a": Infinity}', 'Before\n{"a":1}', '```json\n{}\n```\nextra'])
def test_json_reader_rejects_ambiguous_or_nonfinite_data(tmp_path, raw):
    from secondlook.handoff import read_json
    path = tmp_path / "response.json"
    path.write_text(raw)
    with pytest.raises(CapsuleError):
        read_json(path, 1000, fenced=True)


def test_json_reader_supports_one_fence_and_enforces_size(tmp_path):
    from secondlook.handoff import read_json
    path = tmp_path / "response.json"
    path.write_text('```json\n{"summary":"A"}\n```\n')
    assert read_json(path, 1000, fenced=True) == {"summary": "A"}
    with pytest.raises(CapsuleError, match="limit|large|exceed"):
        read_json(path, 5, fenced=True)
