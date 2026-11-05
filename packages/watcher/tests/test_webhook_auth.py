"""Webhook Authorization header: sent verbatim when configured, never logged."""

from __future__ import annotations

import contextlib
import io
import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

from papaj_watcher.alerts import AlertSink
from papaj_watcher.config import settings_from_args

SECRET = "Bearer test-secret-xyz"


class _Capture(BaseHTTPRequestHandler):
    seen: list[dict] = []

    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")
        _Capture.seen.append({"auth": self.headers.get("Authorization"), "body": body})
        self.send_response(204)
        self.end_headers()

    def log_message(self, *args):
        pass


def _payload():
    return {"ts": "t", "level": "warning", "rule": "r", "message": "m", "should_stop": False}


class WebhookAuthTest(unittest.TestCase):
    def setUp(self):
        _Capture.seen = []
        self.server = HTTPServer(("127.0.0.1", 0), _Capture)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.server.server_port}/hook"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()

    def _emit(self, sink):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            sink.emit(_payload())
        return out.getvalue() + err.getvalue()

    def test_auth_header_sent_verbatim_and_not_logged(self):
        logs = self._emit(AlertSink(webhook_url=self.url, webhook_auth=SECRET))
        self.assertEqual(_Capture.seen[0]["auth"], SECRET)
        self.assertNotIn("test-secret-xyz", logs)

    def test_no_auth_header_by_default(self):
        self._emit(AlertSink(webhook_url=self.url))
        self.assertIsNone(_Capture.seen[0]["auth"])

    def test_failure_message_does_not_leak_secret(self):
        sink = AlertSink(webhook_url="http://127.0.0.1:1/nothing", webhook_auth=SECRET)
        self.assertNotIn("test-secret-xyz", self._emit(sink))

    def test_cli_flag_and_settings_repr_hide_secret(self):
        settings = settings_from_args(["--webhook", self.url, "--webhook-auth", SECRET])
        self.assertEqual(settings.webhook_auth, SECRET)
        self.assertNotIn("test-secret-xyz", repr(settings))


if __name__ == "__main__":
    unittest.main()
