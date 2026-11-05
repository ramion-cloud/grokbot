"""Main poll loop for Papaj Watcher."""

from __future__ import annotations

import signal
import sys
import time
from typing import Any

from .alerts import AlertSink, finding_payload
from .client import ClientError, DashboardClient
from .config import Settings, settings_from_args
from .evidence import save_evidence
from .rules import Finding, RuleEngine, is_latched
from .vision import VisionAnalyzer


class PapajWatcher:
    def __init__(self, settings: Settings, client: DashboardClient | None = None) -> None:
        self.settings = settings
        self.client = client or DashboardClient(settings.url, settings.timeout_s)
        self.rules = RuleEngine(settings.thresholds)
        self.alerts = AlertSink(settings.log_path, settings.webhook_url)
        self.vision = None
        if settings.vlm_enabled:
            if not settings.vlm_base_url:
                raise SystemExit("VLM is enabled but no --vlm-base-url / PAPAJ_VLM_BASE_URL was set")
            self.vision = VisionAnalyzer(
                settings.vlm_base_url,
                settings.vlm_api_key,
                settings.vlm_model,
                timeout_s=settings.vlm_timeout_s,
                can_stop=settings.vlm_can_stop,
            )
        self._stop = False
        self.last_stop_response: dict[str, Any] | None = None

    def request_shutdown(self, *_args: Any) -> None:
        self._stop = True

    def run(self) -> int:
        mode = "STOP ENABLED" if self.settings.enable_stop else "DRY-RUN (stop disabled)"
        print(
            f"Papaj Watcher starting against {self.settings.url} every {self.settings.interval_s:.2f}s "
            f"[{mode}] cameras={','.join(self.settings.cameras)}",
            flush=True,
        )
        cycles = 0
        while not self._stop:
            try:
                self.poll_once()
            except ClientError as exc:
                print(f"dashboard error: {exc}", file=sys.stderr, flush=True)
            except Exception as exc:
                print(f"watcher cycle failed: {exc}", file=sys.stderr, flush=True)
            cycles += 1
            if self.settings.once:
                break
            deadline = time.monotonic() + self.settings.interval_s
            while not self._stop and time.monotonic() < deadline:
                time.sleep(min(0.2, deadline - time.monotonic()))
        print(f"Papaj Watcher stopped after {cycles} cycle(s).", flush=True)
        return 0

    def poll_once(self, now: float | None = None) -> list[Finding]:
        ts = time.time() if now is None else now
        state = self.client.get_state()
        findings = self.rules.evaluate(state, ts)
        frames: dict[str, bytes] = {}
        need_frames = bool(findings) or self.vision is not None
        if need_frames:
            for role in self.settings.cameras:
                try:
                    jpeg = self.client.get_snapshot(role)
                except ClientError as exc:
                    print(f"camera {role} failed: {exc}", file=sys.stderr, flush=True)
                    continue
                if jpeg:
                    frames[role] = jpeg
        if self.vision is not None and frames:
            findings.extend(self.vision.analyze(frames, state))

        evidence_paths: list[str] = []
        if findings and self.settings.evidence_dir is not None and frames:
            evidence_paths = save_evidence(self.settings.evidence_dir, ts, frames, findings)
        elif findings and self.settings.evidence_dir is not None and not frames:
            # Still write a metadata-only note if cameras were empty.
            evidence_paths = save_evidence(self.settings.evidence_dir, ts, {"none": b""}, findings)

        critical_stop = any(item.should_stop for item in findings) and not is_latched(state)
        stop_requested = False
        if critical_stop:
            if self.settings.enable_stop:
                self.last_stop_response = self.client.send_stop(enabled=True)
                stop_requested = True
            else:
                print(
                    "DRY-RUN: a critical finding would POST /api/stop (tokenless hold). "
                    "Re-run with --enable-stop to actually stop the arm.",
                    flush=True,
                )

        if not findings:
            print(f"[{time.strftime('%H:%M:%S')}] ok  sequence={state.get('sequence')} age_s={state.get('age_s')}", flush=True)
            return findings

        dry_run = not self.settings.enable_stop
        for item in findings:
            payload = finding_payload(
                item,
                ts,
                dry_run=dry_run,
                stop_requested=stop_requested and item.should_stop,
                evidence=evidence_paths,
            )
            self.alerts.emit(payload)
        return findings


def main(argv: list[str] | None = None) -> int:
    settings = settings_from_args(argv)
    watcher = PapajWatcher(settings)
    signal.signal(signal.SIGINT, watcher.request_shutdown)
    signal.signal(signal.SIGTERM, watcher.request_shutdown)
    return watcher.run()
