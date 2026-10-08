import json

import pytest

from secondlook.core import write_json
from secondlook.evaluate import evaluate
from secondlook.report import write_report
from secondlook.runner import run
from test_rebuild import rebuild_capsule


def test_explicit_null_context_completes_after_provider_response(rebuild_capsule, tmp_path, monkeypatch):
    import secondlook.runner as runner
    data = json.loads(rebuild_capsule.read_text())
    data['context'] = None
    write_json(rebuild_capsule, data)

    class Provider:
        def preflight(self):
            return 'test-only'

        def call(self, prompt, schema, budget, receipt):
            return {'output': {'summary': 'Repair greeting', 'edits': [{'path': 'index.html', 'old': 'Wrong', 'new': 'Hello'}]},
                    'cost_usd': .01, 'models': ['test-model'], 'usage': {'input_tokens': 10, 'output_tokens': 10}}

    monkeypatch.setattr(runner, 'ClaudeProvider', lambda model: Provider())
    result = run(rebuild_capsule, tmp_path/'run', mode='ordinary')
    assert result['status'] == 'completed'
    assert result['arms']['B']['evaluation']['passed'] == 2
    assert result['cost']['total_usd'] == .01 and result['model_calls'] == 1


@pytest.mark.parametrize('method', ['POST', 'PUT', 'DELETE'])
def test_readonly_input_preserves_static_server_rejection(tmp_path, method):
    source = tmp_path/'source'; source.mkdir()
    (source/'facts.json').write_text('{"name":"Original"}')
    (source/'index.html').write_text('<h1></h1><script>fetch("facts.json",{method:'+json.dumps(method)+'}).then(r=>document.querySelector("h1").textContent=String(r.status))</script>')
    checks = [{'id':'method','inputs':{'facts.json':{'name':'Override'}},
               'assert':{'selector':'h1','text':'501'}}]
    result = evaluate(source, checks, tmp_path/'evidence', readonly_files=['facts.json'])
    assert result['status'] == 'completed' and result['passed'] == 1


def test_readonly_head_has_metadata_without_a_response_body(tmp_path):
    source = tmp_path/'source'; source.mkdir()
    (source/'facts.json').write_text('{}')
    (source/'index.html').write_text('<h1></h1><script>fetch("facts.json",{method:"HEAD"}).then(async r=>document.querySelector("h1").textContent=r.status+":"+(await r.text()).length)</script>')
    result = evaluate(source, [{'id':'head','inputs':{'facts.json':{'name':'Override'}},
        'assert':{'selector':'h1','text':'200:0'}}],tmp_path/'evidence',readonly_files=['facts.json'])
    assert result['passed'] == 1


def test_report_harness_errors_are_unmeasured_not_behavior_failures(tmp_path):
    checks = [{'id':'invalid','category':'intent','basis':'Requirement'},
              {'id':'broken','category':'preservation','basis':'Existing behavior'}]
    result = {'status':'inconclusive','capsule':{'checks':checks},
        'arms':{'B':{'evaluation':{'status':'error','passed':0,'total':2,'checks':[
            {'id':'invalid','passed':False,'error_kind':'harness','error':'Invalid test selector'},
            {'id':'broken','passed':False,'error_kind':'behavior','error':'Expected element missing'}]}}}}
    html = write_report(result,tmp_path).read_text()
    assert 'class="badge unknown" title="Invalid test selector">UNKNOWN' in html
    assert '<i class="unknown" title="invalid"' in html
    assert 'class="badge fail" title="Expected element missing">FAIL' in html
    assert html.count('<i class="bad"') == 1
