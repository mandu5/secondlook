import json

import pytest

from secondlook.core import CapsuleError, load_capsule, write_json
from secondlook.evaluate import evaluate
from secondlook.runner import build_prompt
from test_rebuild import rebuild_capsule


def test_case_inputs_are_readonly_per_context_and_never_prompted(rebuild_capsule, tmp_path):
    source = rebuild_capsule.parent / "app"
    (source / 'index.html').write_text('<h1></h1><script>fetch("facts.json?cache=123").then(r=>r.json()).then(d=>document.querySelector("h1").textContent=d.public_fact)</script>')
    original = (source / 'facts.json').read_bytes()
    data = json.loads(rebuild_capsule.read_text())
    data['checks'] = [
        {'id': 'hidden-input', 'inputs': {'facts.json': {'public_fact': 'WITHHELD_CASE_INPUT'}},
         'assert': {'selector': 'h1', 'text': 'WITHHELD_CASE_INPUT'}},
        {'id': 'original-input', 'assert': {'selector': 'h1', 'text': 'Shared factual input'}},
    ]
    write_json(rebuild_capsule, data)
    capsule = load_capsule(rebuild_capsule)
    result = evaluate(source, capsule['checks'], tmp_path / 'evaluation', readonly_files=capsule['readonly_files'])
    assert result['status'] == 'completed' and result['passed'] == 2
    assert (source / 'facts.json').read_bytes() == original
    bundle = {name: (source / name).read_text() for name in capsule['files']}
    for phase in ('ordinary', 'reframe', 'implement_reframe', 'rebuild'):
        assert 'WITHHELD_CASE_INPUT' not in build_prompt(capsule, bundle, phase)


@pytest.mark.parametrize('inputs', [
    {'index.html': {'tamper': True}}, {'not-allowlisted.json': {}}, {'../escape.json': {}},
    {'facts.json': 'already encoded JSON'}, {'facts.json': {'large': 'x' * 65_537}}, None,
])
def test_inputs_cannot_override_implementation_or_exceed_contract(rebuild_capsule, inputs):
    data = json.loads(rebuild_capsule.read_text())
    data['checks'][0]['inputs'] = inputs
    write_json(rebuild_capsule, data)
    with pytest.raises(CapsuleError, match='input|Input'):
        load_capsule(rebuild_capsule)
