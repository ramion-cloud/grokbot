"""CLI and environment configuration for Papaj Watcher."""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

DEFAULT_DASHBOARD_URL = "http://127.0.0.1:8780"
LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})
CAMERA_ROLES = ("overhead", "wrist", "observer")

# Conservative SO-101 velocity caps used when /api/state has no max_vel map.
DEFAULT_MAX_VEL_DEG_S = {
    "shoulder_pan": 140.0,
    "shoulder_lift": 120.0,
    "elbow_flex": 120.0,
    "wrist_flex": 160.0,
    "wrist_roll": 220.0,
    "gripper": 300.0,
}


@dataclass
class Thresholds:
    """Deterministic rule thresholds. Override via JSON config or env PAPAJ_THRESHOLDS_JSON."""

    limit_warning_deg: float = 8.0
    limit_critical_deg: float = 3.0
    velocity_warning_ratio: float = 0.85
    velocity_critical_ratio: float = 1.10
    default_max_vel_deg_s: dict[str, float] = field(
        default_factory=lambda: dict(DEFAULT_MAX_VEL_DEG_S)
    )
    temperature_warning_c: float = 60.0
    temperature_critical_c: float = 75.0
    current_warning: float = 800.0
    current_critical: float = 1200.0
    load_warning: float = 80.0
    load_critical: float = 95.0
    tracking_error_warning_deg: float = 15.0
    tracking_error_critical_deg: float = 30.0
    command_burst_window_s: float = 1.0
    command_burst_warning: int = 8
    command_burst_critical: int = 16
    lease_expiry_warning_s: float = 0.35
    stale_sample_warning_s: float = 1.5
    stale_sample_critical_s: float = 3.0
    owner_flicker_window_s: float = 5.0
    owner_flicker_count: int = 3
    motion_epsilon_deg: float = 1.5
    emit_cooldown_s: float = 2.0

    def overlay(self, data: dict[str, Any]) -> "Thresholds":
        known = {item.name for item in fields(self)}
        updates: dict[str, Any] = {}
        for key, value in data.items():
            if key not in known:
                continue
            if key == "default_max_vel_deg_s" and isinstance(value, dict):
                merged = dict(self.default_max_vel_deg_s)
                for joint, vel in value.items():
                    try:
                        merged[str(joint)] = float(vel)
                    except (TypeError, ValueError):
                        continue
                updates[key] = merged
            else:
                updates[key] = value
        return replace_thresholds(self, **updates)


def replace_thresholds(base: Thresholds, **updates: Any) -> Thresholds:
    payload = asdict(base)
    payload.update(updates)
    return Thresholds(**payload)


@dataclass
class Settings:
    url: str = DEFAULT_DASHBOARD_URL
    interval_s: float = 1.0
    cameras: tuple[str, ...] = CAMERA_ROLES
    timeout_s: float = 8.0
    enable_stop: bool = False
    confirm_remote_stop: bool = False
    log_path: Path | None = None
    evidence_dir: Path | None = None
    webhook_url: str | None = None
    webhook_auth: str | None = field(default=None, repr=False)
    vlm_enabled: bool = False
    vlm_base_url: str | None = None
    vlm_api_key: str | None = None
    vlm_model: str = "gpt-4o-mini"
    vlm_timeout_s: float = 20.0
    vlm_can_stop: bool = False
    once: bool = False
    intent_enabled: bool = True
    intent_window_s: float = 60.0
    intent_cooldown_s: float = 30.0
    thresholds: Thresholds = field(default_factory=Thresholds)

    def is_remote_host(self) -> bool:
        host = (urlparse(self.url).hostname or "").lower()
        return host not in LOOPBACK_HOSTS

    def validate_stop_safety(self) -> None:
        if not self.enable_stop:
            return
        if self.is_remote_host() and not self.confirm_remote_stop:
            raise SystemExit(
                "Refusing --enable-stop against a non-loopback dashboard "
                f"({self.url}). Re-run with --confirm-remote-stop only if you "
                "really intend to POST /api/stop to that host (tokenless "
                "STOP holds the arm and revokes the operator lease)."
            )


def _truthy(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _optional_path(value: str | None) -> Path | None:
    if not value:
        return None
    return Path(value).expanduser()


def load_thresholds(path: Path | None, raw_json: str | None) -> Thresholds:
    thresholds = Thresholds()
    if path is not None:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("Thresholds file must contain a JSON object")
        thresholds = thresholds.overlay(data)
    if raw_json:
        data = json.loads(raw_json)
        if not isinstance(data, dict):
            raise ValueError("PAPAJ_THRESHOLDS_JSON must be a JSON object")
        thresholds = thresholds.overlay(data)
    return thresholds


def parse_cameras(value: str | None) -> tuple[str, ...]:
    if not value:
        return CAMERA_ROLES
    cameras = tuple(item.strip() for item in value.split(",") if item.strip())
    unknown = [name for name in cameras if name not in CAMERA_ROLES]
    if unknown:
        raise SystemExit(f"Unknown camera role(s): {', '.join(unknown)}")
    return cameras or CAMERA_ROLES


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="papaj-watcher",
        description=(
            "Poll Ramion dashboard camera snapshots and /api/state, emit "
            "warnings, and optionally POST tokenless STOP on critical events."
        ),
    )
    parser.add_argument(
        "--url",
        default=os.environ.get("RAMION_DASHBOARD_URL", DEFAULT_DASHBOARD_URL),
        help="Dashboard base URL (default: %(default)s or RAMION_DASHBOARD_URL)",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=float(os.environ.get("PAPAJ_INTERVAL", "1.0")),
        help="Poll interval in seconds (default: 1.0, env PAPAJ_INTERVAL)",
    )
    parser.add_argument(
        "--cameras",
        default=os.environ.get("PAPAJ_CAMERAS", ",".join(CAMERA_ROLES)),
        help="Comma-separated camera roles: overhead,wrist,observer",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=float(os.environ.get("PAPAJ_TIMEOUT", "8.0")),
        help="HTTP timeout in seconds for dashboard requests",
    )
    parser.add_argument(
        "--log",
        default=os.environ.get("PAPAJ_LOG"),
        help="JSONL warning log path (env PAPAJ_LOG)",
    )
    parser.add_argument(
        "--evidence",
        default=os.environ.get("PAPAJ_EVIDENCE"),
        help="Directory for annotated evidence frames (env PAPAJ_EVIDENCE)",
    )
    parser.add_argument(
        "--webhook",
        default=os.environ.get("PAPAJ_WEBHOOK_URL"),
        help="Warning webhook URL, e.g. a Grok Bot routine trigger (env PAPAJ_WEBHOOK_URL)",
    )
    parser.add_argument(
        "--webhook-auth",
        default=os.environ.get("PAPAJ_WEBHOOK_AUTH"),
        help="Authorization header value sent verbatim with webhook POSTs, e.g. 'Bearer xyz' "
        "(env PAPAJ_WEBHOOK_AUTH). Never logged.",
    )
    parser.add_argument(
        "--config",
        default=os.environ.get("PAPAJ_CONFIG"),
        help="JSON file of threshold overrides (env PAPAJ_CONFIG)",
    )
    parser.add_argument(
        "--enable-stop",
        action="store_true",
        default=_truthy(os.environ.get("PAPAJ_ENABLE_STOP")),
        help="POST /api/stop on critical rule hits. Default OFF (dry-run).",
    )
    parser.add_argument(
        "--confirm-remote-stop",
        action="store_true",
        default=_truthy(os.environ.get("PAPAJ_CONFIRM_REMOTE_STOP")),
        help="Required together with --enable-stop when the dashboard URL is not loopback.",
    )
    parser.add_argument(
        "--vlm",
        action="store_true",
        default=_truthy(os.environ.get("PAPAJ_VLM_ENABLED")),
        help="Send snapshots to a pluggable VLM endpoint for unsafe-behavior warnings",
    )
    parser.add_argument(
        "--vlm-base-url",
        default=os.environ.get("PAPAJ_VLM_BASE_URL"),
        help="OpenAI-compatible or local VLM base URL (env PAPAJ_VLM_BASE_URL)",
    )
    parser.add_argument(
        "--vlm-model",
        default=os.environ.get("PAPAJ_VLM_MODEL", "gpt-4o-mini"),
        help="VLM model name (env PAPAJ_VLM_MODEL)",
    )
    parser.add_argument(
        "--vlm-timeout",
        type=float,
        default=float(os.environ.get("PAPAJ_VLM_TIMEOUT", "20.0")),
        help="VLM HTTP timeout in seconds",
    )
    parser.add_argument(
        "--vlm-can-stop",
        action="store_true",
        default=_truthy(os.environ.get("PAPAJ_VLM_CAN_STOP")),
        help="Allow critical VLM findings to request STOP (still requires --enable-stop)",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Poll a single cycle and exit",
    )
    parser.add_argument(
        "--no-intent",
        action="store_true",
        help="Disable session intent scoring (enabled by default)",
    )
    parser.add_argument(
        "--intent-window",
        type=float,
        default=float(os.environ.get("PAPAJ_INTENT_WINDOW", "60")),
        help="Intent sliding window in seconds (env PAPAJ_INTENT_WINDOW)",
    )
    parser.add_argument(
        "--intent-cooldown",
        type=float,
        default=float(os.environ.get("PAPAJ_INTENT_COOLDOWN", "30")),
        help="Intent alert cooldown in seconds (env PAPAJ_INTENT_COOLDOWN)",
    )
    return parser


def settings_from_args(argv: list[str] | None = None) -> Settings:
    args = build_parser().parse_args(argv)
    thresholds = load_thresholds(
        Path(args.config).expanduser() if args.config else None,
        os.environ.get("PAPAJ_THRESHOLDS_JSON"),
    )
    settings = Settings(
        url=args.url.rstrip("/"),
        interval_s=max(0.1, float(args.interval)),
        cameras=parse_cameras(args.cameras),
        timeout_s=max(0.5, float(args.timeout)),
        enable_stop=bool(args.enable_stop),
        confirm_remote_stop=bool(args.confirm_remote_stop),
        log_path=_optional_path(args.log),
        evidence_dir=_optional_path(args.evidence),
        webhook_url=args.webhook or None,
        webhook_auth=args.webhook_auth or None,
        vlm_enabled=bool(args.vlm),
        vlm_base_url=args.vlm_base_url or None,
        vlm_api_key=os.environ.get("PAPAJ_VLM_API_KEY") or os.environ.get("OPENAI_API_KEY"),
        vlm_model=args.vlm_model,
        vlm_timeout_s=max(1.0, float(args.vlm_timeout)),
        vlm_can_stop=bool(args.vlm_can_stop),
        once=bool(args.once),
        intent_enabled=(not bool(args.no_intent)) and (
            True if os.environ.get("PAPAJ_INTENT") is None else _truthy(os.environ.get("PAPAJ_INTENT"))
        ),
        intent_window_s=max(5.0, float(args.intent_window)),
        intent_cooldown_s=max(1.0, float(args.intent_cooldown)),
        thresholds=thresholds,
    )
    settings.validate_stop_safety()
    return settings
