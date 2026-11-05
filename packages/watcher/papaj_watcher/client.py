"""Read-only dashboard HTTP client. STOP is posted only when explicitly enabled."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .config import CAMERA_ROLES


class ClientError(RuntimeError):
    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


@dataclass(frozen=True)
class HttpResponse:
    status: int
    content_type: str
    body: bytes


class DashboardClient:
    """HTTP client for a Ramion-style dashboard URL (see RAMION_DASHBOARD_URL).

    GET /api/state              JSON joint/state telemetry
    GET /cameras/{role}.jpg     JPEG snapshot (overhead, wrist, observer)
    POST /api/stop              tokenless STOP (never called unless enabled=True)
    """

    def __init__(self, base_url: str, timeout_s: float = 8.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_s = timeout_s

    def get_state(self) -> dict[str, Any]:
        response = self.request("GET", "/api/state")
        if response.status != 200:
            raise ClientError(
                f"GET /api/state returned HTTP {response.status}", response.status
            )
        try:
            payload = json.loads(response.body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ClientError(f"GET /api/state returned invalid JSON: {exc}") from exc
        if not isinstance(payload, dict):
            raise ClientError("GET /api/state did not return a JSON object")
        return payload

    def get_snapshot(self, role: str) -> bytes | None:
        if role not in CAMERA_ROLES:
            raise ValueError(f"Unknown camera role: {role}")
        response = self.request("GET", f"/cameras/{role}.jpg")
        if response.status != 200 or not response.body:
            return None
        return response.body

    def send_stop(self, *, enabled: bool) -> dict[str, Any]:
        """POST /api/stop with an empty JSON object. Tokenless by design.

        `enabled` must be True. The watcher only passes that when --enable-stop
        (and live-host confirmation, if needed) is set. This method will not
        fire against a dashboard just because someone imported the client.
        """
        if not enabled:
            raise RuntimeError("send_stop() refused: dry-run guard (enabled=False)")
        response = self.request(
            "POST",
            "/api/stop",
            body=b"{}",
            headers={"Content-Type": "application/json"},
        )
        if response.status >= 400:
            raise ClientError(
                f"POST /api/stop returned HTTP {response.status}", response.status
            )
        if not response.body:
            return {"status": response.status}
        try:
            payload = json.loads(response.body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return {"status": response.status, "raw": response.body.decode("utf-8", "replace")}
        return payload if isinstance(payload, dict) else {"status": response.status, "body": payload}

    def request(
        self,
        method: str,
        path: str,
        body: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> HttpResponse:
        url = self.base_url + path
        request_headers = {"User-Agent": "papaj-watcher/0.1", "Accept": "*/*"}
        if headers:
            request_headers.update(headers)
        request = Request(url, data=body, headers=request_headers, method=method)
        try:
            with urlopen(request, timeout=self.timeout_s) as response:
                return HttpResponse(
                    status=getattr(response, "status", 200),
                    content_type=response.headers.get("Content-Type") or "",
                    body=response.read(),
                )
        except HTTPError as exc:
            payload = b""
            try:
                payload = exc.read()
            except Exception:
                payload = b""
            return HttpResponse(
                status=int(exc.code),
                content_type=(exc.headers.get("Content-Type") if exc.headers else "") or "",
                body=payload,
            )
        except URLError as exc:
            raise ClientError(f"{method} {path} failed: {exc.reason}") from exc
