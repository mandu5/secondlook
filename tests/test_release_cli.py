import json
import os
from pathlib import Path
import subprocess
import sys

from secondlook.core import load_capsule
from secondlook.runner import run
from secondlook.provider import ProviderError
from test_cli import cli
from test_rebuild import rebuild_capsule


def test_init_explicit_criteria_probe_real_behavior_and_independent_brief(tmp_path):
    app = tmp_path / 'app'
    app.mkdir()
    (app / 'index.html').write_text('<h1>Draft</h1><a href="/docs">Docs</a>')
    brief = tmp_path / 'requirements.txt'
    brief.write_text('Show Hello in the page heading and retain the Docs link.')
    capsule = tmp_path / 'capsule.json'
    proc = cli('init', app, '--intent', 'Welcome a reader', '--files', 'index.html',
               '--expect-text', 'role=heading', 'Hello', '--preserve-text', 'role=link', 'Docs',
               '--brief-file', brief, '--output', capsule)
    assert proc.returncode == 0, proc.stderr
    data = load_capsule(capsule)
    assert data['intent']['confirmed'] is False and data['rebuild']['confirmed'] is False
    assert data['rebuild']['brief'] == brief.read_text()
    assert [c['category'] for c in data['checks']] == ['intent', 'preservation']
    proc = cli('probe', capsule, '--output', tmp_path / 'probe')
    assert proc.returncode == 0, proc.stderr
    evidence = json.loads((tmp_path / 'probe' / 'result.json').read_text())
    assert evidence['model_calls'] == 0
    assert evidence['arms']['A']['evaluation']['passed'] == 1
    assert evidence['arms']['A']['evaluation']['total'] == 2
    confirmed = tmp_path / 'confirmed.json'
    proc = cli('init', app, '--intent', 'Welcome a reader', '--files', 'index.html',
               '--expect-text', 'role=heading', 'Hello', '--preserve-text', 'role=link', 'Docs',
               '--brief-file', brief, '--confirm-intent', '--output', confirmed)
    assert proc.returncode == 0, proc.stderr
    assert load_capsule(confirmed)['rebuild']['confirmed'] is True


def test_init_invalid_contract_leaves_no_output_and_never_overwrites(tmp_path):
    app = tmp_path / 'app'; app.mkdir()
    (app / 'index.html').write_text('<h1>Hello</h1>')
    brief = tmp_path / 'brief.txt'; brief.write_text('Hello')
    output = tmp_path / 'capsule.json'
    proc = cli('init', app, '--intent', 'Hello', '--files', 'index.html',
               '--brief-file', brief, '--output', output)
    assert proc.returncode == 2 and not output.exists()
    output.write_text('keep original')
    proc = cli('init', app, '--intent', 'Hello', '--files', 'index.html',
               '--expect-text', 'h1', 'Hello', '--output', output)
    assert proc.returncode == 2 and output.read_text() == 'keep original'


def test_doctor_launches_chromium_without_model_or_account():
    proc = cli('doctor')
    assert proc.returncode == 0, proc.stderr
    result = json.loads(proc.stdout)
    assert result['ready'] is True and result['model_calls'] == 0
    assert any(c['name'] == 'chromium' and c['ok'] for c in result['checks'])
    assert all(c['name'] != 'provider' for c in result['checks'])


def test_doctor_missing_browser_has_actionable_failure(tmp_path):
    proc = subprocess.run([sys.executable, '-m', 'secondlook', 'doctor'],
        env={**os.environ, 'PYTHONPATH': str(Path(__file__).parents[1] / 'src'),
             'PLAYWRIGHT_BROWSERS_PATH': str(tmp_path / 'no-browsers')}, capture_output=True, text=True, timeout=30)
    assert proc.returncode == 1
    result = json.loads(proc.stdout)
    assert result['ready'] is False and result['model_calls'] == 0
    assert 'python -m playwright install' in next(c for c in result['checks'] if c['name'] == 'chromium')['fix']


def test_budget_stopped_arms_keep_baseline_comparisons(rebuild_capsule, tmp_path, monkeypatch):
    import secondlook.runner as runner

    class UnknownProvider:
        def preflight(self):
            return 'test-only'

        def call(self, prompt, schema, budget, receipt):
            raise ProviderError('Dispatch outcome unknown', None)

    monkeypatch.setattr(runner, 'ClaudeProvider', lambda model: UnknownProvider())
    result = run(rebuild_capsule, tmp_path / 'run', mode='compare-three')
    assert result['model_calls'] == 1 and result['cost']['total_usd'] is None
    assert result['arms']['C']['status'] == result['arms']['D']['status'] == 'skipped_budget'
    assert result['comparisons']['A_C']['verdict'] == 'inconclusive'
    assert result['comparisons']['A_D']['verdict'] == 'inconclusive'
