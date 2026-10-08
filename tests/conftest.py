import json

import pytest


@pytest.fixture
def capsule_file(tmp_path):
    root = tmp_path / "app"
    root.mkdir()
    (root / "index.html").write_text('<h1 id="title">Hello</h1>')
    data = {
        "version": 1,
        "id": "hello",
        "title": "Hello app",
        "intent": {"text": "Show Hello", "source": "User request", "confirmed": True},
        "root": "app",
        "files": ["index.html"],
        "entrypoint": "index.html",
        "baseline": {"model": "unknown", "provenance": "existing artifact"},
        "constraints": ["Keep the heading"],
        "assumptions": [],
        "failures": ["The title is wrong"],
        "revisit": {"capabilities": ["coding"], "impact": 3, "estimated_usd": 0.5},
        "checks": [{"id": "title", "name": "Title", "actions": [], "assert": {"selector": "h1", "text": "Hello"}}],
    }
    path = tmp_path / "capsule.json"
    path.write_text(json.dumps(data))
    return path

