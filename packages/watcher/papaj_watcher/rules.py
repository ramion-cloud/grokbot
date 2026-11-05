"""Deterministic safety rules over successive /api/state snapshots."""

from __future__ import annotations

import math
import re
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Iterable

from .config import Thresholds

LEVEL_INFO = "info"
LEVEL_WARNING = "warning"
LEVEL_CRITICAL = "critical"

FAULT_CRITICAL_RE = re.compile(
    r"overload|przeci[aą]żenie|przeciazenie|overheat|przegrzanie|"
    r"overcurrent|za du[zż]y pr[aą]d|za duzy prad|stall|collision|"
    r"napiecie zasilania poza zakresem|voltage",
    re.IGNORECASE,
)


@dataclass
class Finding:
    level: str
    rule: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    should_stop: bool = False


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def float_map(value: Any) -> dict[str, float]:
    if not isinstance(value, dict):
        return {}
    out: dict[str, float] = {}
    for key, item in value.items():
        if _is_number(item):
            out[str(key)] = float(item)
    return out


def limit_map(value: Any) -> dict[str, tuple[float, float]]:
    if not isinstance(value, dict):
        return {}
    out: dict[str, tuple[float, float]] = {}
    for key, pair in value.items():
        if isinstance(pair, (list, tuple)) and len(pair) == 2 and _is_number(pair[0]) and _is_number(pair[1]):
            low, high = float(pair[0]), float(pair[1])
            out[str(key)] = (min(low, high), max(low, high))
    return out


def extract_series(state: dict[str, Any], names: Iterable[str]) -> dict[str, float]:
    bags: list[dict[str, Any]] = [state]
    telemetry = state.get("telemetry")
    if isinstance(telemetry, dict):
        bags.append(telemetry)
    for bag in bags:
        for name in names:
            raw = bag.get(name)
            mapped = float_map(raw)
            if mapped:
                return mapped
            if _is_number(raw):
                return {"robot": float(raw)}
    return {}


def is_latched(state: dict[str, Any]) -> bool:
    emergency = state.get("emergency_stop")
    return isinstance(emergency, dict) and emergency.get("latched") is True


def moving(state: dict[str, Any], epsilon: float) -> bool:
    measured = float_map(state.get("measured"))
    target = float_map(state.get("target"))
    command = float_map(state.get("command"))
    joints = set(measured) | set(target) | set(command)
    for joint in joints:
        if joint in measured and joint in target and abs(target[joint] - measured[joint]) > epsilon:
            return True
        if joint in measured and joint in command and abs(command[joint] - measured[joint]) > epsilon:
            return True
    return False


def owner_id(state: dict[str, Any]) -> str | None:
    control = state.get("control")
    if not isinstance(control, dict):
        return None
    value = control.get("owner_id")
    if value is None or value == "":
        return None
    return str(value)


def sample_age(state: dict[str, Any]) -> float | None:
    if _is_number(state.get("age_s")):
        return float(state["age_s"])
    sample = state.get("sample")
    if isinstance(sample, dict) and _is_number(sample.get("age_s")):
        return float(sample["age_s"])
    return None


class RuleEngine:
    """Stateful evaluator. Feed successive /api/state payloads."""

    def __init__(self, thresholds: Thresholds | None = None) -> None:
        self.thresholds = thresholds or Thresholds()
        self._prev: dict[str, Any] | None = None
        self._prev_ts: float | None = None
        self._command_changes: deque[float] = deque()
        self._owner_changes: deque[tuple[float, str | None]] = deque()
        self._last_owner: str | None = None
        self._seen_owner = False
        self._last_emit: dict[str, float] = {}

    def evaluate(self, state: dict[str, Any], now: float) -> list[Finding]:
        findings: list[Finding] = []
        findings.extend(self._joint_limits(state))
        findings.extend(self._velocity(state, now))
        findings.extend(self._temperature(state))
        findings.extend(self._current(state))
        findings.extend(self._load_and_tracking(state))
        findings.extend(self._faults(state))
        findings.extend(self._command_bursts(state, now))
        findings.extend(self._lease(state, now))
        findings.extend(self._health(state))

        if is_latched(state):
            for item in findings:
                item.should_stop = False

        emitted: list[Finding] = []
        cooldown = self.thresholds.emit_cooldown_s
        for item in findings:
            key = f"{item.rule}:{item.level}:{item.details.get('joint', '')}"
            last = self._last_emit.get(key)
            if last is not None and cooldown > 0 and now - last < cooldown:
                continue
            self._last_emit[key] = now
            emitted.append(item)

        self._prev = state
        self._prev_ts = now
        return emitted

    def _emit(
        self,
        level: str,
        rule: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> Finding:
        return Finding(
            level=level,
            rule=rule,
            message=message,
            details=details or {},
            should_stop=(level == LEVEL_CRITICAL),
        )

    def _joint_limits(self, state: dict[str, Any]) -> list[Finding]:
        findings: list[Finding] = []
        measured = float_map(state.get("measured"))
        limits = limit_map(state.get("limits"))
        warn_m = self.thresholds.limit_warning_deg
        crit_m = self.thresholds.limit_critical_deg
        for joint, position in measured.items():
            if joint not in limits:
                continue
            low, high = limits[joint]
            span = high - low
            if span <= 0:
                continue
            headroom = min(position - low, high - position)
            if headroom <= crit_m:
                findings.append(
                    self._emit(
                        LEVEL_CRITICAL,
                        "joint_near_limits",
                        f"{joint} is {headroom:.1f} deg from its limit ({position:.1f} in [{low:.1f}, {high:.1f}])",
                        {"joint": joint, "position": position, "limit_low": low, "limit_high": high, "headroom_deg": headroom},
                    )
                )
            elif headroom <= warn_m:
                findings.append(
                    self._emit(
                        LEVEL_WARNING,
                        "joint_near_limits",
                        f"{joint} is {headroom:.1f} deg from its limit ({position:.1f} in [{low:.1f}, {high:.1f}])",
                        {"joint": joint, "position": position, "limit_low": low, "limit_high": high, "headroom_deg": headroom},
                    )
                )
        if state.get("clip"):
            findings.append(
                self._emit(
                    LEVEL_WARNING,
                    "joint_near_limits",
                    f"Controller reported a clipped target: {state.get('clip')}",
                    {"clip": state.get("clip")},
                )
            )
        return findings

    def _max_vel(self, state: dict[str, Any], joint: str) -> float:
        configured = float_map(state.get("max_vel"))
        if joint in configured and configured[joint] > 0:
            return configured[joint]
        defaults = self.thresholds.default_max_vel_deg_s
        if joint in defaults and defaults[joint] > 0:
            return defaults[joint]
        return 120.0

    def _velocity(self, state: dict[str, Any], now: float) -> list[Finding]:
        if self._prev is None or self._prev_ts is None:
            return []
        dt = now - self._prev_ts
        if dt < 0.05:
            return []
        prev = float_map(self._prev.get("measured"))
        current = float_map(state.get("measured"))
        findings: list[Finding] = []
        for joint, position in current.items():
            if joint not in prev:
                continue
            speed = abs(position - prev[joint]) / dt
            cap = self._max_vel(state, joint)
            if cap <= 0:
                continue
            ratio = speed / cap
            details = {"joint": joint, "velocity_deg_s": speed, "max_vel_deg_s": cap, "ratio": ratio, "dt_s": dt}
            if ratio >= self.thresholds.velocity_critical_ratio:
                findings.append(
                    self._emit(
                        LEVEL_CRITICAL,
                        "velocity_spike",
                        f"{joint} velocity {speed:.1f} deg/s exceeds {self.thresholds.velocity_critical_ratio:.2f}x cap {cap:.1f}",
                        details,
                    )
                )
            elif ratio >= self.thresholds.velocity_warning_ratio:
                findings.append(
                    self._emit(
                        LEVEL_WARNING,
                        "velocity_spike",
                        f"{joint} velocity {speed:.1f} deg/s is {ratio:.2f}x cap {cap:.1f}",
                        details,
                    )
                )
        return findings

    def _threshold_series(
        self,
        state: dict[str, Any],
        names: tuple[str, ...],
        rule: str,
        unit: str,
        warning_at: float,
        critical_at: float,
        label: str,
    ) -> list[Finding]:
        series = extract_series(state, names)
        findings: list[Finding] = []
        for joint, value in series.items():
            details = {"joint": joint, "value": value, "unit": unit}
            if value >= critical_at:
                findings.append(
                    self._emit(
                        LEVEL_CRITICAL,
                        rule,
                        f"{label} on {joint} is {value:.1f}{unit} (critical >={critical_at:.1f})",
                        details,
                    )
                )
            elif value >= warning_at:
                findings.append(
                    self._emit(
                        LEVEL_WARNING,
                        rule,
                        f"{label} on {joint} is {value:.1f}{unit} (warning >={warning_at:.1f})",
                        details,
                    )
                )
        return findings

    def _temperature(self, state: dict[str, Any]) -> list[Finding]:
        return self._threshold_series(
            state,
            ("temperatures", "temperature", "present_temperature", "temp_c"),
            "temperature_spike",
            "C",
            self.thresholds.temperature_warning_c,
            self.thresholds.temperature_critical_c,
            "Temperature",
        )

    def _current(self, state: dict[str, Any]) -> list[Finding]:
        return self._threshold_series(
            state,
            ("currents", "current", "present_current", "current_ma"),
            "current_spike",
            "",
            self.thresholds.current_warning,
            self.thresholds.current_critical,
            "Current",
        )

    def _load_and_tracking(self, state: dict[str, Any]) -> list[Finding]:
        findings = self._threshold_series(
            state,
            ("loads", "load", "present_load", "torque_load"),
            "collision_torque",
            "%",
            self.thresholds.load_warning,
            self.thresholds.load_critical,
            "Load",
        )
        measured = float_map(state.get("measured"))
        command = float_map(state.get("command"))
        for joint, position in measured.items():
            if joint not in command:
                continue
            error = abs(command[joint] - position)
            details = {"joint": joint, "tracking_error_deg": error, "measured": position, "command": command[joint]}
            if error >= self.thresholds.tracking_error_critical_deg:
                findings.append(
                    self._emit(
                        LEVEL_CRITICAL,
                        "collision_torque",
                        f"{joint} tracking error {error:.1f} deg looks like a stall or collision",
                        details,
                    )
                )
            elif error >= self.thresholds.tracking_error_warning_deg:
                findings.append(
                    self._emit(
                        LEVEL_WARNING,
                        "collision_torque",
                        f"{joint} tracking error {error:.1f} deg (command vs measured)",
                        details,
                    )
                )
        return findings

    def _faults(self, state: dict[str, Any]) -> list[Finding]:
        faults = state.get("faults")
        if not isinstance(faults, list):
            return []
        findings: list[Finding] = []
        for item in faults:
            text = str(item)
            if FAULT_CRITICAL_RE.search(text):
                findings.append(
                    self._emit(
                        LEVEL_CRITICAL,
                        "collision_torque",
                        f"Servo fault: {text}",
                        {"fault": text},
                    )
                )
            else:
                findings.append(
                    self._emit(
                        LEVEL_WARNING,
                        "collision_torque",
                        f"Servo fault: {text}",
                        {"fault": text},
                    )
                )
        return findings

    def _command_fingerprint(self, state: dict[str, Any]) -> tuple[tuple[str, float], ...]:
        target = float_map(state.get("target"))
        command = float_map(state.get("command"))
        keys = sorted(set(target) | set(command))
        fingerprint = []
        for key in keys:
            value = target.get(key, command.get(key, 0.0))
            fingerprint.append((key, round(value, 3)))
        return tuple(fingerprint)

    def _command_bursts(self, state: dict[str, Any], now: float) -> list[Finding]:
        fingerprint = self._command_fingerprint(state)
        prev_fp = self._command_fingerprint(self._prev) if self._prev is not None else None
        if prev_fp is not None and fingerprint != prev_fp:
            self._command_changes.append(now)
        window = self.thresholds.command_burst_window_s
        while self._command_changes and now - self._command_changes[0] > window:
            self._command_changes.popleft()
        count = len(self._command_changes)
        details = {"changes": count, "window_s": window}
        if count >= self.thresholds.command_burst_critical:
            return [
                self._emit(
                    LEVEL_CRITICAL,
                    "rapid_command_bursts",
                    f"{count} target/command changes in {window:.1f}s",
                    details,
                )
            ]
        if count >= self.thresholds.command_burst_warning:
            return [
                self._emit(
                    LEVEL_WARNING,
                    "rapid_command_bursts",
                    f"{count} target/command changes in {window:.1f}s",
                    details,
                )
            ]
        return []

    def _lease(self, state: dict[str, Any], now: float) -> list[Finding]:
        findings: list[Finding] = []
        current_owner = owner_id(state)
        if not self._seen_owner:
            self._last_owner = current_owner
            self._seen_owner = True
        elif current_owner != self._last_owner:
            self._owner_changes.append((now, current_owner))
            self._last_owner = current_owner
        window = self.thresholds.owner_flicker_window_s
        while self._owner_changes and now - self._owner_changes[0][0] > window:
            self._owner_changes.popleft()
        if len(self._owner_changes) >= self.thresholds.owner_flicker_count:
            findings.append(
                self._emit(
                    LEVEL_WARNING,
                    "lease_anomaly",
                    f"Control owner changed {len(self._owner_changes)} times in {window:.1f}s",
                    {"changes": len(self._owner_changes), "window_s": window},
                )
            )

        control = state.get("control") if isinstance(state.get("control"), dict) else {}
        expires = control.get("expires_in_s") if isinstance(control, dict) else None
        in_motion = moving(state, self.thresholds.motion_epsilon_deg)
        torque_on = state.get("torque") is True
        if in_motion and current_owner is None and not is_latched(state):
            findings.append(
                self._emit(
                    LEVEL_CRITICAL,
                    "lease_anomaly",
                    "Arm command/target differs from measured pose with no control lease owner",
                    {"torque": torque_on, "expires_in_s": expires},
                )
            )
        if (
            current_owner is not None
            and _is_number(expires)
            and float(expires) <= self.thresholds.lease_expiry_warning_s
            and in_motion
        ):
            findings.append(
                self._emit(
                    LEVEL_WARNING,
                    "lease_anomaly",
                    f"Control lease expires in {float(expires):.2f}s while the arm is still moving",
                    {"expires_in_s": float(expires)},
                )
            )
        return findings

    def _health(self, state: dict[str, Any]) -> list[Finding]:
        findings: list[Finding] = []
        age = sample_age(state)
        if age is not None:
            if age >= self.thresholds.stale_sample_critical_s:
                findings.append(
                    self._emit(
                        LEVEL_CRITICAL,
                        "lease_anomaly",
                        f"Joint telemetry is stale ({age:.2f}s old)",
                        {"age_s": age},
                    )
                )
            elif age >= self.thresholds.stale_sample_warning_s:
                findings.append(
                    self._emit(
                        LEVEL_WARNING,
                        "lease_anomaly",
                        f"Joint telemetry is aging ({age:.2f}s old)",
                        {"age_s": age},
                    )
                )
        if state.get("connected") is False:
            findings.append(
                self._emit(
                    LEVEL_CRITICAL,
                    "lease_anomaly",
                    "Controller reports the arm is disconnected",
                    {"connected": False},
                )
            )
        elif state.get("loop_ok") is False:
            findings.append(
                self._emit(
                    LEVEL_WARNING,
                    "lease_anomaly",
                    "Controller control loop is not OK",
                    {"loop_ok": False},
                )
            )
        return findings
