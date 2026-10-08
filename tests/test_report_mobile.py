from playwright.sync_api import sync_playwright

from secondlook.report import write_report


def test_frozen_check_fingerprint_does_not_overflow_mobile_report(tmp_path):
    result = {'status': 'probe_completed', 'kind': 'baseline_probe',
        'capsule': {'checks': [{'id': 'x', 'category': 'intent', 'basis': 'Purpose'}]},
        'arms': {'A': {'evaluation': {'status':'completed','passed':0,'total':1,'checks':[{'id':'x','passed':False}]}}},
        'manifest': {'checks': 'a' * 64, 'checks_frozen_at': '2026-10-08T00:00:00.000000+00:00'}}
    path = write_report(result, tmp_path)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width':390,'height':844})
        page.goto(path.as_uri())
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
        browser.close()
