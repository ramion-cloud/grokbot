"""Offline end-to-end replay: fake dashboard + capture webhook, both on 127.0.0.1.

Scripted shoulder_pan sequence -30 -> -65 -> -70 -> -40 -> -68 must produce a
forbidden_zone finding, then a suspicious and a bad_intent intent_alert (demo: true),
delivered with the Authorization header. Any POST to the fake dashboard fails the check.
"""

from __future__ import annotations

import copy
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "tests"))

from papaj_watcher.config import settings_from_args  # noqa: E402
from papaj_watcher.watcher import PapajWatcher  # noqa: E402
from support import load_state  # noqa: E402

SEQUENCE = [-30.0, -65.0, -70.0, -40.0, -68.0]
AUTH = "Bearer offline-demo-check"
dashboard_posts: list[str] = []
webhook_hits: list[dict] = []
cursor = {"i": 0}


def state_for(value: float) -> dict:
    state = copy.deepcopy(load_state())
    for key in ("measured", "command", "target"):
        state[key]["shoulder_pan"] = value
    return state


class Dashboard(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        if self.path == "/api/state":
            value = SEQUENCE[min(cursor["i"], len(SEQUENCE) - 1)]
            body = json.dumps(state_for(value)).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):  # noqa: N802
        dashboard_posts.append(self.path)
        self.send_response(403)
        self.end_headers()

    def log_message(self, *args):
        pass


class Webhook(BaseHTTPRequestHandler):
    def do_POST(self):  # noqa: N802
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
        webhook_hits.append({"auth": self.headers.get("Authorization"), "body": body})
        self.send_response(204)
        self.end_headers()

    def log_message(self, *args):
        pass


def serve(handler):
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def main() -> int:
    dash, hook = serve(Dashboard), serve(Webhook)
    settings = settings_from_args([
        "--url", f"http://127.0.0.1:{dash.server_port}",
        "--config", str(HERE / "thresholds.demo.json"),
        "--webhook", f"http://127.0.0.1:{hook.server_port}/hook",
        "--webhook-auth", AUTH,
        "--cameras", "overhead",
    ])
    assert not settings.enable_stop, "replay must run in dry-run"
    watcher = PapajWatcher(settings)
    for i in range(len(SEQUENCE)):
        cursor["i"] = i
        print(f"--- tick {i}: shoulder_pan={SEQUENCE[i]}", flush=True)
        watcher.poll_once(now=1000.0 + i)
    dash.shutdown()
    hook.shutdown()

    findings = [h["body"] for h in webhook_hits if h["body"].get("rule") == "forbidden_zone"]
    alerts = [h["body"] for h in webhook_hits if h["body"].get("type") == "intent_alert"]
    errors = []
    if dashboard_posts:
        errors.append(f"dashboard received POSTs: {dashboard_posts}")
    if not findings:
        errors.append("no forbidden_zone finding delivered")
    elif "below demo limit -60°" not in findings[0]["message"]:
        errors.append(f"unexpected message: {findings[0]['message']}")
    levels = [a["level"] for a in alerts]
    if levels != ["suspicious", "bad_intent"]:
        errors.append(f"intent levels {levels}, expected ['suspicious', 'bad_intent']")
    if alerts and alerts[-1].get("recommended_action") != "revoke_access_human_review":
        errors.append(f"last action {alerts[-1].get('recommended_action')}")
    for a in alerts:
        if a.get("demo") is not True or not a["slack_text"]["text"].startswith("[DEMO]"):
            errors.append("intent_alert missing demo flag or [DEMO] prefix")
        if a.get("dry_run") is not True:
            errors.append("intent_alert not dry_run")
    if any(h["auth"] != AUTH for h in webhook_hits):
        errors.append("webhook call without the expected Authorization header")

    print(f"webhook deliveries: {len(webhook_hits)} (forbidden_zone findings: {len(findings)}, intent_alerts: {levels})")
    if errors:
        for e in errors:
            print("FAIL:", e)
        return 1
    print("PASS: forbidden_zone -> suspicious -> bad_intent (revoke_access_human_review), auth header ok, no POST to dashboard")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
