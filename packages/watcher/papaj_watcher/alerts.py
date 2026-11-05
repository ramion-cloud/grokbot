"""Stdout, JSONL, and webhook emitters for watcher findings."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from .rules import Finding

WARSAW = ZoneInfo("Europe/Warsaw")


def now_local(ts: float | None = None) -> datetime:
    if ts is None:
        return datetime.now(WARSAW)
    return datetime.fromtimestamp(ts, tz=timezone.utc).astimezone(WARSAW)


def finding_payload(
    finding: Finding,
    ts: float,
    *,
    dry_run: bool,
    stop_requested: bool,
    evidence: list[str] | None = None,
) -> dict[str, Any]:
    stamp = now_local(ts)
    return {
        "source": "papaj-watcher",
        "ts": stamp.isoformat(),
        "ts_epoch": ts,
        "level": finding.level,
        "rule": finding.rule,
        "message": finding.message,
        "details": finding.details,
        "should_stop": finding.should_stop,
        "dry_run": dry_run,
        "stop_requested": stop_requested,
        "evidence": evidence or [],
    }


class AlertSink:
    def __init__(
        self,
        log_path: Path | None = None,
        webhook_url: str | None = None,
        webhook_auth: str | None = None,
    ) -> None:
        self.log_path = log_path
        self.webhook_url = webhook_url
        # Sent verbatim as the Authorization header; never printed or logged.
        self._webhook_auth = webhook_auth or None
        if self.log_path is not None:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def emit(self, payload: dict[str, Any]) -> None:
        if payload.get("type") == "intent_alert":
            session = payload.get("session") if isinstance(payload.get("session"), dict) else {}
            who = session.get("label") or session.get("owner_id") or "unleased"
            line = (
                f"[{payload.get('ts')}] INTENT {str(payload.get('level', '')).upper()} "
                f"score={payload.get('score')} action={payload.get('recommended_action')} "
                f"session={who}"
            )
        else:
            line = (
                f"[{payload['ts']}] {payload['level'].upper()} {payload['rule']}: {payload['message']}"
            )
            if payload.get("should_stop"):
                if payload.get("dry_run"):
                    line += "  [DRY-RUN would POST /api/stop]"
                elif payload.get("stop_requested"):
                    line += "  [STOP requested]"
                else:
                    line += "  [STOP indicated]"
        print(line, flush=True)
        if self.log_path is not None:
            with self.log_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(payload, ensure_ascii=True) + "\n")
        if self.webhook_url:
            self._post_webhook(payload)

    def _post_webhook(self, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
        headers = {"Content-Type": "application/json", "User-Agent": "papaj-watcher/0.1"}
        if self._webhook_auth:
            headers["Authorization"] = self._webhook_auth
        request = Request(
            self.webhook_url,
            data=body,
            headers=headers,
            method="POST",
        )
        try:
            with urlopen(request, timeout=8) as response:
                response.read()
        except Exception as exc:
            print(f"webhook failed: {type(exc).__name__}: {_redact(str(exc), self._webhook_auth)}", file=sys.stderr, flush=True)


def _redact(text: str, secret: str | None) -> str:
    if secret:
        text = text.replace(secret, "[redacted]")
    return text


def describe_url_error(exc: URLError) -> str:
    return str(exc.reason)
