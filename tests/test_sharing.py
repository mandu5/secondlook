import base64
import json

import pytest

from test_cli import cli


PRIVATE = 'PRIVATE_MARKER_94_no_publish'
PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=')


@pytest.fixture
def private_result(tmp_path):
    root = tmp_path / 'run'; root.mkdir()
    (root / 'screen.png').write_bytes(PNG)
    checks = [{'id': PRIVATE, 'name': PRIVATE, 'category': 'intent', 'basis': PRIVATE,
               'assert': {'selector': PRIVATE, 'text': PRIVATE}, 'inputs': {PRIVATE: [PRIVATE]}}]
    result = {'version': 1, 'kind': 'live_model', 'status': 'inconclusive', 'output': PRIVATE,
        'created_at': PRIVATE, 'capsule': {'title': PRIVATE, 'checks': checks,
        'intent': {'text': PRIVATE, 'source': PRIVATE, 'confirmed': True, 'provenance': {PRIVATE: PRIVATE}},
        'baseline': {'provenance': PRIVATE}, 'root': PRIVATE, 'files': [PRIVATE],
        'rebuild': {'brief': PRIVATE, 'source': PRIVATE, 'confirmed': True}},
        'arms': {'A': {'label': PRIVATE, 'status': 'completed', 'models': ['unknown'], 'cost_usd': 0,
            'tokens': {'total': 0}, 'evaluation': {'status': 'completed', 'passed': 0, 'total': 1,
            'checks': [{'id': PRIVATE, 'passed': False, 'error_kind': 'behavior', 'error': PRIVATE}],
            'screenshots': {PRIVATE: str(root / 'screen.png')}}, 'diff': PRIVATE, 'brief': PRIVATE},
        'B': {'label': PRIVATE, 'status': 'remote_outcome_unknown', 'models': [PRIVATE],
              'tokens': {'total': None}, 'cost_usd': None, 'error': PRIVATE,
              'calls': [PRIVATE], 'receipts': [PRIVATE], 'summary': PRIVATE}},
        'comparisons': {'A_B': {'verdict': 'inconclusive', 'improvements': [], 'regressions': [], 'reason': PRIVATE}},
        'cost': {'total_usd': None, 'known_spend_usd': .02, 'limit_usd': 1, 'basis': PRIVATE},
        'manifest': {'source': 'a' * 64, 'checks': 'b' * 64, 'provider_version': PRIVATE, 'output': PRIVATE},
        'model_calls': 1, 'source_unchanged': True, 'error': PRIVATE, 'source_context': {PRIVATE: PRIVATE}}
    path = root / 'result.json'; path.write_text(json.dumps(result))
    return path


def test_metrics_only_export_excludes_every_private_surface(private_result, tmp_path):
    output = tmp_path / 'shared'
    proc = cli('share', private_result, '--output', output)
    assert proc.returncode == 0, proc.stderr
    assert {p.name for p in output.iterdir()} == {'index.html', 'summary.json'}
    for path in output.iterdir():
        text = path.read_text()
        assert PRIVATE not in text and str(tmp_path) not in text
        assert 'data:image/png' not in text and 'capsule.frozen.json' not in text
    data = json.loads((output / 'summary.json').read_text())
    assert data['cost']['total_usd'] is None and data['cost']['known_spend_usd'] == .02
    assert data['arms']['B']['tokens']['total'] is None
    assert data['arms']['A']['evaluation']['checks'][0]['passed'] is False
    html = (output / 'index.html').read_text()
    assert 'Inconclusive run' in html and 'summary.json' in html
    assert 'Raw call receipts and prompts are in the receipts folder' not in html


def test_export_explicit_intent_and_screenshot_are_portable_and_escaped(private_result, tmp_path):
    output = tmp_path / 'shared'
    title = '<script>window.pwned=1</script>'
    proc = cli('share', private_result, '--output', output, '--include-intent', '--include-screenshots', '--title', title)
    assert proc.returncode == 0, proc.stderr
    html = (output / 'index.html').read_text()
    assert PRIVATE in html and 'data:image/png;base64,' in html
    assert title not in html and '&lt;script&gt;' in html
    data = json.loads((output / 'summary.json').read_text())
    assert data['capsule']['intent']['text'] == PRIVATE
    assert 'provenance' not in data['capsule']['intent']
    assert str(tmp_path) not in json.dumps(data)


@pytest.mark.parametrize('image', ['escape', 'symlink', 'missing', 'not_png', 'oversized'])
def test_export_refuses_unconfined_or_invalid_screenshots(private_result, tmp_path, image):
    outside = tmp_path / 'private.png'; outside.write_bytes(PNG)
    candidate = private_result.parent / 'screen.png'
    if image == 'escape':
        candidate = outside
    elif image == 'symlink':
        candidate.unlink(); candidate.symlink_to(outside)
    elif image == 'missing':
        candidate.unlink()
    elif image == 'not_png':
        candidate.write_bytes(b'not an image')
    elif image == 'oversized':
        with candidate.open('wb') as stream:
            stream.write(PNG); stream.truncate(21 * 1024 * 1024)
    data = json.loads(private_result.read_text())
    data['arms']['A']['evaluation']['screenshots'] = {'initial': str(candidate)}
    private_result.write_text(json.dumps(data))
    output = tmp_path / 'shared'
    proc = cli('share', private_result, '--output', output, '--include-screenshots')
    assert proc.returncode == 2 and not output.exists()


@pytest.mark.parametrize('value', [-1, float('nan'), True])
def test_export_refuses_malformed_cost(private_result, tmp_path, value):
    data = json.loads(private_result.read_text()); data['cost']['total_usd'] = value
    private_result.write_text(json.dumps(data))
    output = tmp_path / 'shared'
    proc = cli('share', private_result, '--output', output)
    assert proc.returncode == 2 and not output.exists()


def test_export_never_replaces_existing_directory(private_result, tmp_path):
    output = tmp_path / 'shared'; output.mkdir()
    (output / 'keep').write_text('original')
    proc = cli('share', private_result, '--output', output)
    assert proc.returncode == 2 and (output / 'keep').read_text() == 'original'


def test_export_preserves_harness_unknowns(private_result, tmp_path):
    data = json.loads(private_result.read_text())
    data['arms']['A']['evaluation']['checks'][0]['error_kind'] = 'harness'
    data['arms']['A']['evaluation']['status'] = 'error'
    private_result.write_text(json.dumps(data))
    proc = cli('share', private_result, '--output', tmp_path / 'shared')
    assert proc.returncode == 0, proc.stderr
    html = (tmp_path / 'shared' / 'index.html').read_text()
    assert '>UNKNOWN</span>' in html and '>FAIL</span>' not in html
