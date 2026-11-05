from __future__ import annotations

import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from urllib.parse import urlsplit

from papaj_watcher.client import DashboardClient
from papaj_watcher.config import Settings, Thresholds, settings_from_args
from papaj_watcher.vision import VisionAnalyzer
from papaj_watcher.watcher import PapajWatcher

from support import FIXTURES, load_state


class Recorder:
    def __init__(self) -> None:
        self.state = load_state()
        self.posts: list[tuple[str, bytes]] = []
        self.jpeg = (FIXTURES / "frame.jpg").read_bytes()
        self.snapshot_status = 200


class FakeDashboard(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        recorder: Recorder = self.server.recorder  # type: ignore[attr-defined]
        if path == "/api/state":
            self._send(200, "application/json", json.dumps(recorder.state).encode())
        elif path == "/api/telemetry":
            self._send(404, "application/json", b'{"error":"not found"}')
        elif path.startswith("/cameras/") and path.endswith(".jpg"):
            if recorder.snapshot_status != 200:
                self._send(recorder.snapshot_status, "application/json", b'{"error":"No fresh camera frame"}')
                return
            self._send(200, "image/jpeg", recorder.jpeg)
        else:
            self._send(404, "application/json", b'{"error":"not found"}')

    def do_POST(self) -> None:
        path = urlsplit(self.path).path
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b""
        recorder: Recorder = self.server.recorder  # type: ignore[attr-defined]
        recorder.posts.append((path, body))
        if path == "/api/stop":
            self._send(200, "application/json", b"{}")
        else:
            self._send(404, "application/json", b'{"error":"not found"}')

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _send(self, status: int, content_type: str, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class FakeVLM(BaseHTTPRequestHandler):
    payload = {"unsafe": True, "severity": "warning", "reason": "hand near the gripper"}

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        if length:
            self.rfile.read(length)
        body = json.dumps({"choices": [{"message": {"content": json.dumps(self.payload)}}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        return


def start_server(handler, recorder=None):
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    if recorder is not None:
        server.recorder = recorder
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address[:2]
    return server, f"http://{host}:{port}"


class SettingsTests(unittest.TestCase):
    def test_default_url_is_loopback_placeholder(self) -> None:
        settings = settings_from_args([])
        self.assertEqual(settings.url, "http://127.0.0.1:8780")
        self.assertFalse(settings.enable_stop)

    def test_enable_stop_on_remote_requires_confirmation(self) -> None:
        with self.assertRaises(SystemExit):
            settings_from_args(["--url", "http://example.invalid:8780", "--enable-stop"])
        settings = settings_from_args(
            ["--url", "http://example.invalid:8780", "--enable-stop", "--confirm-remote-stop"]
        )
        self.assertTrue(settings.enable_stop)
        self.assertTrue(settings.confirm_remote_stop)

    def test_enable_stop_on_loopback_does_not_need_confirmation(self) -> None:
        settings = settings_from_args(["--url", "http://127.0.0.1:8780", "--enable-stop"])
        self.assertTrue(settings.enable_stop)
        self.assertFalse(settings.is_remote_host())


class ClientAndWatcherTests(unittest.TestCase):
    def setUp(self) -> None:
        self.recorder = Recorder()
        self.server, self.base = start_server(FakeDashboard, self.recorder)

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()

    def _settings(self, **updates: Any) -> Settings:
        payload = dict(
            url=self.base,
            enable_stop=False,
            confirm_remote_stop=False,
            once=True,
            cameras=("overhead",),
            timeout_s=2.0,
            thresholds=Thresholds(emit_cooldown_s=0.0),
        )
        payload.update(updates)
        return Settings(**payload)

    def test_client_reads_state_and_snapshot(self) -> None:
        client = DashboardClient(self.base, timeout_s=2.0)
        state = client.get_state()
        self.assertEqual(state["robot"], "so101")
        frame = client.get_snapshot("overhead")
        self.assertTrue(frame and frame.startswith(b"\xff\xd8"))

    def test_missing_snapshot_returns_none(self) -> None:
        self.recorder.snapshot_status = 503
        client = DashboardClient(self.base, timeout_s=2.0)
        self.assertIsNone(client.get_snapshot("wrist"))

    def test_dry_run_never_posts_stop(self) -> None:
        self.recorder.state = load_state("state_near_limit.json")
        with TemporaryDirectory() as tmp:
            watcher = PapajWatcher(self._settings(evidence_dir=Path(tmp)))
            findings = watcher.poll_once(now=10.0)
            saved = list(Path(tmp).glob("*"))
        self.assertTrue(any(item.should_stop for item in findings))
        self.assertEqual(self.recorder.posts, [])
        self.assertTrue(any(path.suffix == ".jpg" for path in saved))
        self.assertTrue(any(path.suffix == ".json" for path in saved))

    def test_enable_stop_posts_only_stop(self) -> None:
        self.recorder.state = load_state("state_near_limit.json")
        watcher = PapajWatcher(self._settings(enable_stop=True))
        findings = watcher.poll_once(now=10.0)
        self.assertTrue(any(item.should_stop for item in findings))
        self.assertEqual([path for path, _body in self.recorder.posts], ["/api/stop"])
        self.assertFalse(any("emergency-stop" in path or "control" in path or "target" in path for path, _ in self.recorder.posts))

    def test_send_stop_guard_without_enabled_flag(self) -> None:
        client = DashboardClient(self.base, timeout_s=2.0)
        with self.assertRaises(RuntimeError):
            client.send_stop(enabled=False)
        self.assertEqual(self.recorder.posts, [])


class VisionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.server, self.base = start_server(FakeVLM)

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()

    def test_vision_warning_does_not_request_stop_by_default(self) -> None:
        analyzer = VisionAnalyzer(self.base, api_key=None, model="fake", timeout_s=2.0, can_stop=False)
        jpeg = (FIXTURES / "frame.jpg").read_bytes()
        findings = analyzer.analyze({"overhead": jpeg}, {"joints": ["gripper"], "torque": True})
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].rule, "vision_unsafe")
        self.assertEqual(findings[0].level, "warning")
        self.assertFalse(findings[0].should_stop)

    def test_vision_critical_can_stop_only_when_allowed(self) -> None:
        FakeVLM.payload = {"unsafe": True, "severity": "critical", "reason": "arm striking the table"}
        self.addCleanup(lambda: setattr(FakeVLM, "payload", {"unsafe": True, "severity": "warning", "reason": "hand near the gripper"}))
        blocked = VisionAnalyzer(self.base, api_key=None, model="fake", timeout_s=2.0, can_stop=False)
        allowed = VisionAnalyzer(self.base, api_key=None, model="fake", timeout_s=2.0, can_stop=True)
        jpeg = (FIXTURES / "frame.jpg").read_bytes()
        self.assertFalse(blocked.analyze({"overhead": jpeg})[0].should_stop)
        self.assertTrue(allowed.analyze({"overhead": jpeg})[0].should_stop)


if __name__ == "__main__":
    unittest.main()
