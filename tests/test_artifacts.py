import json

import pytest

from secondlook.artifacts import capture_artifact, context_spans
from secondlook.core import CapsuleError, apply_edits, load_capsule, source_bundle


def projected(capsule_file, html):
    data = json.loads(capsule_file.read_text())
    data["context"] = {"index.html": {"mode": "html_scripts"}}
    capsule_file.write_text(json.dumps(data))
    (capsule_file.parent / "app" / "index.html").write_bytes(html.encode())
    return load_capsule(capsule_file)


def test_large_runtime_blob_never_enters_selected_context(capsule_file):
    data = "PRIVATE_ASSET_" + "x" * 100000
    html = '<script type="application/json">' + json.dumps({"assets": data}) + '</script><h1>옷장</h1><script>const label="안녕";</script>'
    capsule = projected(capsule_file, html)
    artifact = capture_artifact(capsule)
    assert artifact.sources == {"index.html": html}
    assert "PRIVATE_ASSET" not in artifact.context["index.html"]
    assert 'const label="안녕";' in artifact.context["index.html"]
    assert artifact.metrics["runtime_bytes"] == len(html.encode())
    assert artifact.metrics["context_bytes"] < 200
    assert source_bundle(capsule) == artifact.context


def test_identity_includes_hidden_data_and_projection(capsule_file):
    capsule = projected(capsule_file, '<script type="application/json">{"secret":1}</script><script>let n=1;</script>')
    first = capture_artifact(capsule)
    (capsule_file.parent / "app" / "index.html").write_text(first.sources["index.html"].replace('"secret":1', '"secret":2'))
    second = capture_artifact(capsule)
    assert first.context == second.context
    assert first.identity != second.identity
    capsule.pop("context")
    assert capture_artifact(capsule).identity != second.identity


def test_script_projection_matches_conservative_executable_types():
    html = '''<p>한글 😀</p><SCRIPT>let plain=1;</SCRIPT>
<script type="module">let moduleValue=2;</script>
<script type="application/json">{"opaque":"yes"}</script>
<script src="app.js">not inline</script>
<script type="text/plain">not code</script>
<script type="application/javascript">let js=3;</script>'''
    ranges = context_spans(html, {"mode": "html_scripts"})
    assert [html[a:b] for a, b in ranges] == ["let plain=1;", "let moduleValue=2;", "let js=3;"]


@pytest.mark.parametrize("policy", [{"mode": "guess"}, {"mode": "html_scripts", "all": True}, "scripts"])
def test_invalid_projection_rejected(capsule_file, policy):
    capsule = projected(capsule_file, "<script>let n=1;</script>")
    capsule["context"]["index.html"] = policy
    with pytest.raises(CapsuleError):
        capture_artifact(capsule)


def test_empty_or_unclosed_selection_refused(capsule_file):
    for html in ['<script type="application/json">{}</script>', '<script>let n=1;']:
        with pytest.raises(CapsuleError):
            capture_artifact(projected(capsule_file, html))


def test_projected_patch_cannot_touch_opaque_regions_and_is_atomic(capsule_file):
    html = '<script type="application/json">{"private":"keep"}</script><h1>옷장</h1><script>let label="before";</script>'
    capsule = projected(capsule_file, html)
    root = capsule_file.parent / "app"
    edits = [{"path": "index.html", "old": '"before"', "new": '"after"'},
             {"path": "index.html", "old": '"keep"', "new": '"leak"'}]
    with pytest.raises(CapsuleError, match="selected|protected"):
        apply_edits(root, edits, ["index.html"], context=capsule["context"])
    assert (root / "index.html").read_text() == html
    apply_edits(root, edits[:1], ["index.html"], context=capsule["context"])
    assert (root / "index.html").read_text() == html.replace('"before"', '"after"')


def test_sequential_unicode_edits_keep_data_bytes(capsule_file):
    html = '<script type="application/json">"'+"x"*100000+'"</script><script>let 값="가";let b="나";</script>'
    capsule = projected(capsule_file, html)
    apply_edits(capsule_file.parent / "app", [
        {"path": "index.html", "old": '"가"', "new": '"가나다😀"'},
        {"path": "index.html", "old": '"나"', "new": '"다"'},
    ], ["index.html"], context=capsule["context"])
    actual = (capsule_file.parent / "app" / "index.html").read_text()
    assert actual == html.replace('"가"','"가나다😀"').replace('"나"','"다"')


def test_projected_source_still_has_a_context_budget(capsule_file):
    with pytest.raises(CapsuleError, match="context"):
        capture_artifact(projected(capsule_file, '<script>'+"x"*70000+'</script>'))


def test_runtime_cap_checked_before_large_read(capsule_file, monkeypatch):
    import secondlook.artifacts as artifacts
    monkeypatch.setattr(artifacts, "MAX_RUNTIME_BYTES", 100)
    with pytest.raises(CapsuleError, match="runtime"):
        capture_artifact(projected(capsule_file, '<script>'+"x"*101+'</script>'))


def test_edit_cannot_reclassify_original_data_then_modify_it(capsule_file):
    html = '<script>let n=1;</script><script type="application/json">{"private":"KEEP"}</script><script>window.ok=1;</script>'
    capsule = projected(capsule_file, html)
    root = capsule_file.parent / "app"
    edits = [{"path": "index.html", "old": "let n=1;", "new": 'let n=1;</script><script data-x="'},
             {"path": "index.html", "old": "KEEP", "new": "CHANGED"}]
    with pytest.raises(CapsuleError, match="protected|boundar"):
        apply_edits(root, edits, capsule["files"], capsule["context"])
    assert (root / "index.html").read_text() == html
    with pytest.raises(CapsuleError, match="boundar|closing|selected"):
        apply_edits(root, edits[:1], capsule["files"], capsule["context"])
    assert (root / "index.html").read_text() == html


@pytest.mark.parametrize("tag", ["textarea", "title", "noscript", "xmp", "iframe", "noembed", "noframes"])
def test_raw_text_is_not_executable_context_or_editable(capsule_file, tag):
    html = f'<{tag}><script>PRIVATE_KEEP</script></{tag}><script>window.ok=1;</script>'
    capsule = projected(capsule_file, html)
    assert "PRIVATE_KEEP" not in source_bundle(capsule)["index.html"]
    with pytest.raises(CapsuleError, match="protected"):
        apply_edits(capsule_file.parent / "app", [{"path": "index.html", "old": "PRIVATE_KEEP", "new": "CHANGED"}], capsule["files"], capsule["context"])


def test_first_duplicate_attribute_controls_script_type(capsule_file):
    html = '<script type="application/json" TYPE="text/javascript">{"private":"KEEP"}</script><script>window.ok=1;</script>'
    capsule = projected(capsule_file, html)
    assert "KEEP" not in source_bundle(capsule)["index.html"]
    with pytest.raises(CapsuleError, match="protected"):
        apply_edits(capsule_file.parent / "app", [{"path": "index.html", "old": "KEEP", "new": "CHANGED"}], capsule["files"], capsule["context"])


@pytest.mark.parametrize("markup", [
    '<plaintext></plaintext><script>PRIVATE</script>',
    '<textarea/><script>PRIVATE</script></textarea>',
    '<svg><script>PRIVATE</script></svg>',
    '<math><script>PRIVATE</script></math>',
    '<template><script>PRIVATE</script></template>',
    '<script><!--<script>PRIVATE</script>hidden</script>',
])
def test_ambiguous_html_projection_fails_closed(markup):
    with pytest.raises(CapsuleError, match="projection|ambiguous|unsupported"):
        context_spans(markup + '<script>window.ok=1;</script>', {"mode": "html_scripts"})


def test_projection_agrees_with_browser_for_review_reproductions():
    from playwright.sync_api import sync_playwright
    html = '<textarea><script>PRIVATE_TEXT</script></textarea><noscript><script>PRIVATE_NOSCRIPT</script></noscript><script type="application/json" type="text/javascript">{"private":1}</script><script>window.ok=1;</script>'
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(html)
        actual = page.evaluate("[...document.querySelectorAll('script')].filter(s=>!s.hasAttribute('src')&&!s.getAttribute('type')).map(s=>s.textContent)")
        browser.close()
    spans = context_spans(html, {"mode": "html_scripts"})
    assert [html[a:b] for a,b in spans] == actual == ["window.ok=1;"]
