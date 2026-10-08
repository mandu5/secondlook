"""Local installation checks. Never dispatches a model request."""

from __future__ import annotations

import platform
import sys

from playwright.sync_api import Error, sync_playwright

from . import __version__
from .provider import ClaudeProvider, ProviderError


def diagnose(*, provider: bool = False) -> dict:
    checks = [{"name": "python", "ok": sys.version_info >= (3, 11),
               "detail": platform.python_version()}]
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(timeout=15_000)
            try:
                page = browser.new_page()
                page.set_content("<h1>Second Look ready</h1>")
                if page.locator("h1").inner_text() != "Second Look ready":
                    raise RuntimeError("Chromium rendered an unexpected page")
                checks.append({"name": "chromium", "ok": True, "detail": browser.version})
            finally:
                browser.close()
    except (Error, OSError, RuntimeError) as error:
        checks.append({"name": "chromium", "ok": False, "detail": str(error),
                       "fix": "Run python -m playwright install chromium. On Linux, use python -m playwright install --with-deps chromium."})
    if provider:
        try:
            version = ClaudeProvider("sonnet").preflight()
            checks.append({"name": "provider", "ok": True, "detail": version,
                           "note": "CLI flags checked. Authentication and model availability are unverified."})
        except ProviderError as error:
            checks.append({"name": "provider", "ok": False, "detail": str(error),
                           "fix": "Install/update and authenticate Claude Code, then run secondlook doctor --provider."})
    return {"version": __version__, "ready": all(c["ok"] for c in checks), "checks": checks, "model_calls": 0}
