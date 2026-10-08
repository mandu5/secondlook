"""Host-owned, declarative browser checks on isolated static app copies."""

from __future__ import annotations

from contextlib import contextmanager
import csv
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import io
import json
from pathlib import Path
import threading
import time
from urllib.parse import urlsplit, quote, unquote

from .core import validate_checks, write_json


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def list_directory(self, path):
        self.send_error(404)
        return None

    def translate_path(self, path):
        translated = Path(super().translate_path(path))
        if not translated.resolve().is_relative_to(Path(self.directory).resolve()):
            return str(Path(self.directory) / "__refused__")
        return str(translated)


@contextmanager
def static_server(root: Path):
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(root)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def evaluate(root: Path, checks: list, output: Path, entrypoint: str = "index.html",
             readonly_files: list[str] | None = None) -> dict:
    validate_checks(checks, readonly_files)
    from playwright.sync_api import sync_playwright, expect, TimeoutError as BrowserTimeout

    output.mkdir(parents=True, exist_ok=True)
    result = {"status": "completed", "checks": [], "passed": 0, "total": len(checks),
              "screenshots": {}, "blocked_requests": [], "page_errors": [],
              "timing_note": "Single local browser runs; includes navigation/actions/waits, not a performance benchmark."}
    blocked = set()
    try:
        with static_server(root) as origin, sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            result["browser_version"] = browser.version

            def new_context(viewport=None, inputs=None):
                context = browser.new_context(viewport=viewport or {"width": 1200, "height": 820}, device_scale_factor=1,
                                              locale="en-US", timezone_id="UTC", service_workers="block")

                def route(request):
                    parsed = urlsplit(request.request.url)
                    if parsed.scheme in {"http", "https"} and parsed.netloc == urlsplit(origin).netloc:
                        name = unquote(parsed.path).removeprefix("/")
                        if name in (inputs or {}) and request.request.method in {"GET", "HEAD"}:
                            payload = json.dumps(inputs[name], ensure_ascii=False, allow_nan=False).encode("utf-8")
                            request.fulfill(status=200, content_type="application/json; charset=utf-8",
                                            headers={"content-length": str(len(payload))},
                                            body=b"" if request.request.method == "HEAD" else payload)
                        else:
                            request.continue_()
                    else:
                        blocked.add(request.request.url)
                        request.abort()

                context.route("**/*", route)
                if hasattr(context, "route_web_socket"):
                    context.route_web_socket("**/*", lambda ws: ws.close())
                context.set_default_timeout(1500)
                return context

            url = origin + "/" + quote(entrypoint, safe="/")
            context = new_context()
            page = context.new_page()
            page.goto(url, wait_until="load", timeout=10000)
            screenshot = output / "initial.png"
            page.screenshot(path=str(screenshot), animations="disabled")
            result["screenshots"]["initial"] = str(screenshot.resolve())
            context.close()
            for check in checks:
                viewport = check.get("viewport", {"width": 1200, "height": 820})
                context = new_context(viewport, check.get("inputs"))
                page = context.new_page()
                page.on("pageerror", lambda error: result["page_errors"].append(str(error)[:500]))
                started = time.monotonic()
                row = {"id": check["id"], "name": check.get("name", check["id"]),
                       "held_out": bool(check.get("held_out", False)), "passed": False, "viewport": viewport}
                if "category" in check:
                    row.update(category=check["category"], basis=check["basis"])
                downloaded = None
                try:
                    page.goto(url, wait_until="load", timeout=10000)
                    for action in check.get("actions", []):
                        if action["type"] == "reload":
                            page.reload(wait_until="load", timeout=10000)
                            continue
                        if action["type"] == "press" and "selector" not in action:
                            page.keyboard.press(action["key"])
                            continue
                        locator = page.locator(action["selector"])
                        # Parse the selector separately: expect() can wrap parser errors
                        # inside AssertionError, which would look like an app failure.
                        locator.count()
                        match action["type"]:
                            case "click":
                                locator.click()
                            case "focus":
                                locator.focus()
                            case "press":
                                locator.press(action["key"])
                            case "fill":
                                locator.fill(action["value"])
                            case "select":
                                locator.select_option(action["value"])
                            case "download":
                                with page.expect_download() as event:
                                    locator.click()
                                download = event.value
                                with open(download.path(), "rb") as stream:
                                    payload = stream.read(1_048_577)
                                if len(payload) > 1_048_576:
                                    raise AssertionError("CSV exceeds 1 MiB check limit")
                                downloaded = list(csv.reader(io.StringIO(payload.decode("utf-8-sig"))))
                    assertion = check["assert"]
                    if "csv" in assertion:
                        if downloaded != assertion["csv"]:
                            raise AssertionError(f"Expected CSV rows {assertion['csv']!r}; received {downloaded!r}")
                    else:
                        locator = page.locator(assertion["selector"])
                        locator.count()
                        if "count" in assertion:
                            expect(locator).to_have_count(assertion["count"], timeout=1500)
                        if "text" in assertion:
                            expect(locator).to_have_text(assertion["text"], timeout=1500)
                        if "value" in assertion:
                            expect(locator).to_have_value(assertion["value"], timeout=1500)
                        if "visible" in assertion:
                            (expect(locator).to_be_visible if assertion["visible"] else expect(locator).to_be_hidden)(timeout=1500)
                        if "focused" in assertion:
                            (expect(locator).to_be_focused if assertion["focused"] else expect(locator).not_to_be_focused)(timeout=1500)
                        if "attribute" in assertion:
                            attribute = assertion["attribute"]
                            expect(locator).to_have_attribute(attribute["name"], attribute["value"], timeout=1500)
                    row["passed"] = True
                except (AssertionError, BrowserTimeout, UnicodeError, csv.Error) as error:
                    row["error_kind"] = "behavior"
                    row["error"] = str(error)[:1200]
                except Exception as error:
                    result["status"] = "error"
                    row["error_kind"] = "harness"
                    row["error"] = str(error)[:1200]
                finally:
                    row["duration_ms"] = round((time.monotonic() - started) * 1000, 2)
                    if check.get("capture"):
                        try:
                            screenshot = output / f"{check['id']}.png"
                            page.screenshot(path=str(screenshot), animations="disabled", timeout=3000)
                            result["screenshots"][check["id"]] = str(screenshot.resolve())
                        except Exception as error:
                            row["screenshot_error"] = str(error)[:300]
                    result["checks"].append(row)
                    context.close()
            browser.close()
    except Exception as error:
        result.update(status="error", error=str(error)[:1500])
    result["passed"] = sum(row["passed"] for row in result["checks"])
    result["blocked_requests"] = sorted(blocked)
    result["categories"] = category_scores(checks, result)
    write_json(output / "evaluation.json", result)
    return result


def category_scores(checks: list, evaluation: dict) -> dict:
    """Do not count a missing or broken check as a measured behavior failure."""
    measured = {row["id"]: row for row in evaluation.get("checks", [])}
    scores = {}
    for check in checks:
        category = check.get("category", "uncategorized")
        score = scores.setdefault(category, {"passed": 0, "failed": 0, "unmeasured": 0, "total": 0})
        score["total"] += 1
        row = measured.get(check["id"])
        field = ("unmeasured" if row is None or row.get("error_kind") == "harness"
                 else "passed" if row["passed"] else "failed")
        score[field] += 1
    return scores


def compare_results(before: dict, after: dict) -> dict:
    result = {"verdict": "inconclusive", "improvements": [], "regressions": [], "unchanged": []}
    left = {c["id"]: c["passed"] for c in before.get("checks", [])}
    right = {c["id"]: c["passed"] for c in after.get("checks", [])}
    if before.get("status") != "completed" or after.get("status") != "completed" or not left or left.keys() != right.keys():
        return result
    for check_id in left:
        bucket = "improvements" if not left[check_id] and right[check_id] else "regressions" if left[check_id] and not right[check_id] else "unchanged"
        result[bucket].append(check_id)
    result["verdict"] = "regression" if result["regressions"] else "improved" if result["improvements"] else "no_measured_gain"
    return result
