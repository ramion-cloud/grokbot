"""Session-level intent risk scoring over Watcher findings and /api/state.

Recommended actions only: this module never calls e-stop and never revokes
access. A soft-stop recommendation is executed by the watcher loop only when
``--enable-stop`` is set.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any

from .alerts import now_local
from .rules import Finding, float_map, is_latched, limit_map, moving, owner_id, sample_age

LEVEL_NORMAL = "normal"
LEVEL_SUSPICIOUS = "suspicious"
LEVEL_BAD_INTENT = "bad_intent"

ACTION_WARN = "warn"
ACTION_SOFT_STOP = "soft_stop"
ACTION_REVIEW = "revoke_access_human_review"
ALLOWED_ACTIONS = (ACTION_WARN, ACTION_SOFT_STOP, ACTION_REVIEW)

PROFILE_NOVICE = "novice"
PROFILE_DELIBERATE = "deliberate"
PROFILE_BENIGN = "benign"

UNLEASED = "unleased"


@dataclass
class IntentConfig:
    window_s: float = 60.0
    cooldown_s: float = 30.0
    suspicious_score: float = 5.0
    bad_intent_score: float = 12.0
    reclaim_after_stop_s: float = 8.0
    motion_after_stop_s: float = 8.0
    motion_epsilon_deg: float = 1.5
    score_jump: float = 3.0
    novice_discount: float = 0.5


@dataclass
class WindowEvent:
    ts: float
    signal: str
    level: str | None = None
    rule: str | None = None
    detail: str = ""
    weight: float = 0.0
    after_warning: bool = False


@dataclass
class SessionState:
    key: str
    owner_id: str | None = None
    label: str | None = None
    events: deque[WindowEvent] = field(default_factory=deque)
    warned_rules: set[str] = field(default_factory=set)
    last_target_fp: tuple[tuple[str, float], ...] | None = None
    last_emit_ts: float | None = None
    last_emit_level: str | None = None
    last_emit_score: float = 0.0
    last_evidence: list[str] = field(default_factory=list)


@dataclass
class IntentAssessment:
    level: str
    score: float
    raw_score: float
    profile: str
    reasons: list[dict[str, Any]]
    recommended_action: str
    session: dict[str, str | None]


def owner_label(state: dict[str, Any]) -> str | None:
    control = state.get("control")
    if not isinstance(control, dict):
        return None
    value = control.get("label")
    if value is None or value == "":
        return None
    return str(value)


def session_key(state: dict[str, Any]) -> str:
    current = owner_id(state)
    return current if current is not None else UNLEASED


def _fingerprint(state: dict[str, Any]) -> tuple[tuple[str, float], ...]:
    target = float_map(state.get("target"))
    command = float_map(state.get("command"))
    keys = sorted(set(target) | set(command))
    out: list[tuple[str, float]] = []
    for key in keys:
        value = target.get(key, command.get(key, 0.0))
        out.append((key, round(value, 3)))
    return tuple(out)


def _level_rank(level: str) -> int:
    return {LEVEL_NORMAL: 0, LEVEL_SUSPICIOUS: 1, LEVEL_BAD_INTENT: 2}.get(level, 0)


def _action_rank(action: str) -> int:
    return {ACTION_WARN: 0, ACTION_SOFT_STOP: 1, ACTION_REVIEW: 2}.get(action, 0)


def format_slack_text(
    *,
    level: str,
    score: float,
    session: dict[str, str | None],
    profile: str,
    reasons: list[dict[str, Any]],
    recommended_action: str,
    dry_run: bool,
) -> dict[str, Any]:
    """Plain-text fallback plus Slack Block Kit JSON, nested as ``slack_text``."""
    owner = session.get("label") or session.get("owner_id") or UNLEASED
    reason_lines = [str(item.get("detail") or item.get("code") or "") for item in reasons]
    reason_lines = [line for line in reason_lines if line]
    text = (
        f"Papaj Watcher intent: {level} "
        f"(score {score:.1f})\n"
        f"Session: {owner}\n"
        f"Profile: {profile}\n"
        f"Recommended action: {recommended_action} (dry_run={str(dry_run).lower()})\n"
        f"Reasons:\n" + ("\n".join(f"- {line}" for line in reason_lines) or "- none")
        + "\nHuman review is required to revoke access. Watcher never e-stops or revokes automatically."
    )
    bullets = "\n".join(f"• {line}" for line in reason_lines) or "• none"
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"Intent {level} (score {score:.1f})", "emoji": True},
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Session:*\n{owner}"},
                {"type": "mrkdwn", "text": f"*Profile:*\n{profile}"},
                {"type": "mrkdwn", "text": f"*Action:*\n`{recommended_action}`"},
                {"type": "mrkdwn", "text": f"*Dry-run:*\n{str(dry_run).lower()}"},
            ],
        },
        {"type": "section", "text": {"type": "mrkdwn", "text": f"*Reasons:*\n{bullets}"}},
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": (
                        "Recommended action only. Soft-stop is gated by `--enable-stop`. "
                        "Never e-stop or revoke access automatically — a human decides."
                    ),
                }
            ],
        },
    ]
    return {"text": text, "blocks": blocks}


class IntentEngine:
    """Aggregate per-session findings into an explainable intent score."""

    def __init__(self, config: IntentConfig | None = None) -> None:
        self.config = config or IntentConfig()
        self.sessions: dict[str, SessionState] = {}
        self.last_owner: str | None = None
        self.last_latched = False
        self.last_stop_ts: float | None = None
        self._vacated_after_stop = False
        self.last_assessment: IntentAssessment | None = None

    def update(
        self,
        state: dict[str, Any],
        findings: list[Finding],
        evidence: list[str] | None,
        now: float,
        *,
        dry_run: bool,
    ) -> dict[str, Any] | None:
        assessment = self.evaluate(state, findings, now)
        session = self.sessions[session_key(state)]
        if evidence:
            session.last_evidence = list(evidence)
        return self.maybe_emit(assessment, session, now, dry_run=dry_run)

    def evaluate(self, state: dict[str, Any], findings: list[Finding], now: float) -> IntentAssessment:
        key = session_key(state)
        session = self.sessions.setdefault(key, SessionState(key=key))
        session.owner_id = owner_id(state)
        if owner_label(state) is not None:
            session.label = owner_label(state)
        self._note_stop_and_claim(state, now)
        self._ingest_state_signals(session, state, now)
        self._ingest_findings(session, findings, now)
        self._prune(session, now)
        assessment = self._score(session, now)
        self.last_assessment = assessment
        return assessment

    def maybe_emit(
        self,
        assessment: IntentAssessment,
        session: SessionState,
        now: float,
        *,
        dry_run: bool,
    ) -> dict[str, Any] | None:
        if assessment.level == LEVEL_NORMAL:
            return None
        if not self._should_emit(session, assessment, now):
            return None
        slack = format_slack_text(
            level=assessment.level,
            score=assessment.score,
            session=assessment.session,
            profile=assessment.profile,
            reasons=assessment.reasons,
            recommended_action=assessment.recommended_action,
            dry_run=dry_run,
        )
        event = {
            "type": "intent_alert",
            "source": "papaj-watcher",
            "ts": now_local(now).isoformat(),
            "ts_epoch": now,
            "level": assessment.level,
            "score": round(assessment.score, 2),
            "session": assessment.session,
            "profile": assessment.profile,
            "reasons": assessment.reasons,
            "evidence": list(session.last_evidence),
            "recommended_action": assessment.recommended_action,
            "dry_run": dry_run,
            "slack_text": slack,
        }
        session.last_emit_ts = now
        session.last_emit_level = assessment.level
        session.last_emit_score = assessment.score
        return event

    def _should_emit(self, session: SessionState, assessment: IntentAssessment, now: float) -> bool:
        if session.last_emit_ts is None:
            return True
        escalated = _level_rank(assessment.level) > _level_rank(session.last_emit_level or LEVEL_NORMAL)
        jumped = assessment.score - session.last_emit_score >= self.config.score_jump
        if escalated or jumped:
            return True
        return (now - session.last_emit_ts) >= self.config.cooldown_s

    def _note_stop_and_claim(self, state: dict[str, Any], now: float) -> None:
        current = owner_id(state)
        latched = is_latched(state)
        if latched and not self.last_latched:
            self.last_stop_ts = now
        if self.last_owner and current is None:
            self.last_stop_ts = now
            self._vacated_after_stop = True
        self.last_owner = current
        self.last_latched = latched

    def _push(self, session: SessionState, event: WindowEvent) -> None:
        session.events.append(event)

    def _ingest_findings(self, session: SessionState, findings: list[Finding], now: float) -> None:
        for item in findings:
            after = item.rule in session.warned_rules
            if item.level == "warning":
                session.warned_rules.add(item.rule)
            elif item.level == "critical" and item.rule in {
                "joint_near_limits",
                "collision_torque",
                "rapid_command_bursts",
                "vision_unsafe",
                "lease_anomaly",
            }:
                session.warned_rules.add(item.rule)
            self._push(
                session,
                WindowEvent(
                    ts=now,
                    signal=item.rule,
                    level=item.level,
                    rule=item.rule,
                    detail=item.message,
                    after_warning=after,
                ),
            )

    def _ingest_state_signals(self, session: SessionState, state: dict[str, Any], now: float) -> None:
        if state.get("clip"):
            self._push(
                session,
                WindowEvent(
                    ts=now,
                    signal="clip_hit",
                    detail=f"Controller reported a clipped target: {state.get('clip')}",
                    weight=2.0,
                ),
            )
        outside = self._targets_outside_limits(state)
        if outside:
            self._push(
                session,
                WindowEvent(
                    ts=now,
                    signal="target_outside_limits",
                    detail="Commanded targets outside joint limits: " + ", ".join(outside),
                    weight=3.0,
                ),
            )
        fingerprint = _fingerprint(state)
        changed = session.last_target_fp is not None and fingerprint != session.last_target_fp
        session.last_target_fp = fingerprint
        age = sample_age(state)
        stale = (
            (age is not None and age >= 1.5)
            or state.get("loop_ok") is False
            or state.get("connected") is False
        )
        if stale and changed:
            self._push(
                session,
                WindowEvent(
                    ts=now,
                    signal="stale_loop_abuse",
                    detail="Targets or commands changed while telemetry was stale or the loop was unhealthy",
                    weight=3.0,
                ),
            )
        cfg = self.config
        if (
            self.last_stop_ts is not None
            and now > self.last_stop_ts
            and now - self.last_stop_ts <= cfg.motion_after_stop_s
            and moving(state, cfg.motion_epsilon_deg)
        ):
            self._push(
                session,
                WindowEvent(
                    ts=now,
                    signal="motion_after_stop",
                    detail="Motion continued right after a soft stop or lease revocation",
                    weight=4.0,
                ),
            )
        if (
            self._vacated_after_stop
            and owner_id(state) is not None
            and self.last_stop_ts is not None
            and now > self.last_stop_ts
            and now - self.last_stop_ts <= cfg.reclaim_after_stop_s
        ):
            recent = any(
                event.signal == "reclaim_after_stop" and now - event.ts < cfg.reclaim_after_stop_s
                for event in session.events
            )
            if not recent:
                self._push(
                    session,
                    WindowEvent(
                        ts=now,
                        signal="reclaim_after_stop",
                        detail="Control was re-claimed immediately after a stop or lease revocation",
                        weight=4.0,
                    ),
                )
            self._vacated_after_stop = False

    def _targets_outside_limits(self, state: dict[str, Any]) -> list[str]:
        limits = limit_map(state.get("limits"))
        target = float_map(state.get("target"))
        hits: list[str] = []
        for joint, value in target.items():
            if joint not in limits:
                continue
            low, high = limits[joint]
            if value < low or value > high:
                hits.append(f"{joint}={value:.1f} not in [{low:.1f}, {high:.1f}]")
        return hits

    def _prune(self, session: SessionState, now: float) -> None:
        window = self.config.window_s
        while session.events and now - session.events[0].ts > window:
            session.events.popleft()

    def _score(self, session: SessionState, now: float) -> IntentAssessment:
        reasons: list[dict[str, Any]] = []
        score = 0.0
        collision_count = 0
        near_limit_after = 0
        has_repeat_warning = False
        escalated_rule = False
        first: dict[str, str] = {}

        for event in session.events:
            weight = event.weight
            if event.signal in {
                "joint_near_limits",
                "rapid_command_bursts",
                "collision_torque",
                "vision_unsafe",
                "lease_anomaly",
                "velocity_spike",
                "temperature_spike",
                "current_spike",
            }:
                table = {
                    "joint_near_limits": (1.0, 2.0),
                    "rapid_command_bursts": (2.0, 4.0),
                    "collision_torque": (2.0, 3.0),
                    "vision_unsafe": (3.0, 5.0),
                    "lease_anomaly": (1.5, 2.5),
                    "velocity_spike": (1.0, 2.0),
                    "temperature_spike": (1.0, 2.5),
                    "current_spike": (1.0, 2.5),
                }
                warn_w, crit_w = table[event.signal]
                weight = crit_w if event.level == "critical" else warn_w
                if event.after_warning:
                    has_repeat_warning = True
                    extra = 3.0 if event.signal == "joint_near_limits" else 1.5
                    if event.signal == "joint_near_limits":
                        near_limit_after += 1
                    weight += extra
                    reasons.append(
                        {
                            "code": f"repeated_{event.signal}_after_warning",
                            "detail": (
                                f"Repeated {event.signal} after an earlier warning"
                                + (f": {event.detail}" if event.detail else "")
                            ),
                            "weight": extra,
                        }
                    )
                prior = first.get(event.signal)
                if prior == "warning" and event.level == "critical":
                    escalated_rule = True
                if event.signal not in first and event.level:
                    first[event.signal] = event.level
                if event.signal == "collision_torque":
                    collision_count += 1
            if weight:
                score += weight
                reasons.append(
                    {
                        "code": event.signal,
                        "detail": event.detail or event.signal,
                        "weight": weight,
                    }
                )

        if collision_count >= 2:
            score += 2.0
            reasons.append(
                {
                    "code": "collision_torque_repeats",
                    "detail": f"collision_torque fired {collision_count} times in the window",
                    "weight": 2.0,
                }
            )

        window = self.config.window_s
        early = sum(1 for event in session.events if event.ts < now - window / 2)
        late = sum(1 for event in session.events if event.ts >= now - window / 2)
        decreasing = late < early
        isolated = len(session.events) <= 3
        high_risk = any(
            event.signal in {"motion_after_stop", "reclaim_after_stop", "stale_loop_abuse"}
            or (event.signal == "vision_unsafe" and event.level == "critical")
            for event in session.events
        )
        deliberate = has_repeat_warning or escalated_rule or high_risk or collision_count >= 2
        novice = (not deliberate) and (decreasing or isolated) and not high_risk
        if not session.events:
            profile = PROFILE_BENIGN
        elif novice:
            profile = PROFILE_NOVICE
        elif deliberate:
            profile = PROFILE_DELIBERATE
        else:
            profile = PROFILE_BENIGN

        raw = score
        if profile == PROFILE_NOVICE:
            score *= self.config.novice_discount
            reasons.append(
                {
                    "code": "novice_pattern",
                    "detail": "Isolated or decreasing activity after warnings — treated as clumsy novice, not deliberate",
                    "weight": -(raw - score),
                }
            )

        if score >= self.config.bad_intent_score:
            level = LEVEL_BAD_INTENT
        elif score >= self.config.suspicious_score:
            level = LEVEL_SUSPICIOUS
        else:
            level = LEVEL_NORMAL

        if profile == PROFILE_NOVICE and level == LEVEL_BAD_INTENT:
            level = LEVEL_SUSPICIOUS

        if level == LEVEL_NORMAL:
            action = ACTION_WARN
        elif level == LEVEL_SUSPICIOUS:
            action = ACTION_WARN
        elif any(event.signal == "reclaim_after_stop" for event in session.events) or any(
            event.signal == "vision_unsafe" and event.level == "critical" for event in session.events
        ):
            action = ACTION_REVIEW
        elif any(event.signal == "motion_after_stop" for event in session.events) and has_repeat_warning:
            action = ACTION_REVIEW
        else:
            action = ACTION_SOFT_STOP

        if profile == PROFILE_NOVICE:
            action = ACTION_WARN

        return IntentAssessment(
            level=level,
            score=round(score, 2),
            raw_score=round(raw, 2),
            profile=profile,
            reasons=reasons,
            recommended_action=action,
            session={"owner_id": session.owner_id, "label": session.label},
        )
