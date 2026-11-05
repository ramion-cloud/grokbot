"""Optional VLM layer: send camera frames to an OpenAI-compatible or local endpoint."""

from __future__ import annotations

import base64
import json
import re
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .rules import LEVEL_CRITICAL, LEVEL_WARNING, Finding

UNSAFE_PROMPT = """You are a hardware safety observer for a tabletop SO-101 robot arm.
Look at this camera frame of a human working with the arm.
Report only physical risk to people or hardware (collision with table/objects, cable wrap,
hands in the pinch/strike zone, arm hitting a camera mount or enclosure, uncontrolled slam).
Do not comment on task quality.
Reply with JSON only, no markdown:
{"unsafe": false, "severity": "none", "reason": "short description"}
severity must be one of: none, warning, critical.
Set unsafe=true only when you see a real risk in the image."""


def _chat_url(base_url: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/chat/completions"):
        return base
    if base.endswith("/v1"):
        return base + "/chat/completions"
    return base + "/v1/chat/completions"


def _extract_json(text: str) -> dict[str, Any] | None:
    stripped = text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", stripped, re.DOTALL)
    if fenced:
        stripped = fenced.group(1)
    try:
        payload = json.loads(stripped)
        return payload if isinstance(payload, dict) else None
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", stripped, re.DOTALL)
        if not match:
            return None
        try:
            payload = json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
        return payload if isinstance(payload, dict) else None


class VisionAnalyzer:
    def __init__(
        self,
        base_url: str,
        api_key: str | None,
        model: str,
        timeout_s: float = 20.0,
        can_stop: bool = False,
    ) -> None:
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self.timeout_s = timeout_s
        self.can_stop = can_stop

    def analyze(self, frames: dict[str, bytes], state: dict[str, Any] | None = None) -> list[Finding]:
        findings: list[Finding] = []
        for role, jpeg in frames.items():
            if not jpeg:
                continue
            try:
                findings.extend(self._analyze_one(role, jpeg, state))
            except Exception as exc:
                findings.append(
                    Finding(
                        level=LEVEL_WARNING,
                        rule="vision_unsafe",
                        message=f"VLM request failed for {role}: {exc}",
                        details={"camera": role, "error": str(exc)},
                        should_stop=False,
                    )
                )
        return findings

    def _analyze_one(self, role: str, jpeg: bytes, state: dict[str, Any] | None) -> list[Finding]:
        image = "data:image/jpeg;base64," + base64.b64encode(jpeg).decode("ascii")
        extras = ""
        if state:
            extras = (
                f" Joint names: {state.get('joints')}. "
                f"Torque={'on' if state.get('torque') else 'off'}. "
                f"E-stop latched={bool((state.get('emergency_stop') or {}).get('latched'))}."
            )
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": UNSAFE_PROMPT + extras},
                        {"type": "image_url", "image_url": {"url": image}},
                    ],
                }
            ],
            "temperature": 0,
        }
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        request = Request(
            _chat_url(self.base_url),
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_s) as response:
                body = response.read()
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace") if exc.fp else ""
            raise RuntimeError(f"HTTP {exc.code} {detail[:200]}") from exc
        except URLError as exc:
            raise RuntimeError(str(exc.reason)) from exc

        try:
            parsed = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"VLM returned non-JSON: {exc}") from exc

        content = ""
        try:
            content = parsed["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            content = json.dumps(parsed)
        if isinstance(content, list):
            texts = [part.get("text", "") for part in content if isinstance(part, dict)]
            content = "\n".join(texts)
        if not isinstance(content, str):
            content = str(content)

        result = _extract_json(content) or {}
        unsafe = bool(result.get("unsafe"))
        severity = str(result.get("severity") or "none").lower()
        reason = str(result.get("reason") or content.strip() or "no reason")
        if not unsafe and severity in {"none", "", "ok", "safe"}:
            return []
        if not unsafe and severity not in {"warning", "critical"}:
            return []
        if severity not in {"warning", "critical"}:
            severity = LEVEL_WARNING
        should_stop = severity == LEVEL_CRITICAL and self.can_stop
        return [
            Finding(
                level=severity,
                rule="vision_unsafe",
                message=f"{role} camera: {reason}",
                details={"camera": role, "severity": severity, "reason": reason},
                should_stop=should_stop,
            )
        ]
