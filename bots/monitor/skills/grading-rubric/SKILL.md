---
name: ramion-grading-rubric
description: >-
  Pass/fail criteria for Ramion hands-on exercises using GET /api/state and
  viewer screenshots. Safety alerts come from Papaj Watcher — do not re-run them.
---

# Grading rubrics

Default **timeout:** 60s from Tutor grade request.
Default **stable samples:** 2 consecutive observations meeting pass condition, sampled every 2–3s.

Use verified `GET /api/state` when HTTP 200; else screenshot-only mode.
Read the payload as documented in `api/contract.md`. Do **not** expect
`gripper.open`, `motion.busy`, or `safety.soft_stopped`.

Report using Monitor output format in `bots/monitor/PERSONA.md`.

Gripper joint name: `state.gripper` if present, otherwise `"gripper"`.
Limits: `limits[joint] = [low, high]`. Span = `high - low`.
Still moving: any joint has `|target[j] - measured[j]| > motion_epsilon_deg`
(`1.5` in `packages/watcher/thresholds.example.json`). Do not invent a second epsilon.

---

## `open-gripper`

| Mode | Pass | Fail |
|------|------|------|
| API | `measured[gripper] >= low + 0.85 * span` and not still moving | Value still near closed at timeout |
| Screenshot | UI shows open state (label “Open”, separated fingers, or open icon) | Closed or ambiguous at timeout |

**Notes:**

- `0.85` / `0.15` are exercise-grade fractions of the gripper range, not Watcher safety thresholds.
- If `emergency_stop.latched === true` mid-exercise → FAIL `unexpected stop`.

---

## `close-gripper`

| Mode | Pass | Fail |
|------|------|------|
| API | `measured[gripper] <= low + 0.15 * span` and not still moving | Still open at timeout |
| Screenshot | Closed icon / “Closed” label | Open at timeout |

---

## `move-home`

| Mode | Pass | Fail |
|------|------|------|
| API | `connected === true`, `loop_ok === true`, and not still moving; screenshot or operator-defined home (live state has no home vector) | Disconnected, latched stop, or clearly not at home at timeout |
| Screenshot | Arm depicted at home/ready pose matching UI legend | Clearly not at home |

---

## Global FAIL reasons (any exercise)

| Reason code | When |
|-------------|------|
| `timeout` | No stable pass within timeout |
| `state mismatch` | API and screenshot disagree |
| `disconnected` | `connected === false` in `GET /api/state` |
| `inconclusive` | Cannot load viewer or API unreachable |
| `unexpected stop` | `emergency_stop.latched === true` during the exercise |
| Watcher `rule` name | A Papaj Watcher alert with `level=critical` arrived during the exercise — copy the Watcher `rule` (for example `collision_torque`), do not invent a parallel name |

---

## Watcher alerts (consume; do not recompute)

Papaj Watcher (`packages/watcher`) is the only rule engine for hardware-safety heuristics. Thresholds are `packages/watcher/thresholds.example.json`.

Monitor reads the same JSON from `PAPAJ_WEBHOOK_URL` or `PAPAJ_LOG` JSONL:

- `source`: `papaj-watcher`
- `level`: `info` | `warning` | `critical`
- `rule`: `joint_near_limits` | `velocity_spike` | `temperature_spike` | `current_spike` | `collision_torque` | `rapid_command_bursts` | `lease_anomaly` | `vision_unsafe`
- `should_stop`: true for `critical` unless the e-stop is already latched
- `dry_run` / `stop_requested`: whether Watcher would or did `POST /api/stop`

Behavior:

| Watcher `level` | During an exercise |
|-----------------|--------------------|
| `critical` | FAIL the exercise; Evidence must include `rule`, `level`, and `message`. Recommend Tutor consider `POST /api/stop` if `should_stop` is true and `dry_run` is true. |
| `warning` | Do not automatic-FAIL. Mention `rule` + `level` in Evidence. |
| `info` | Ignore for grading. |

Never re-evaluate joint proximity, velocity, temperature, current, load, tracking error, command bursts, or lease flicker inside this rubric.

---

## Global INCONCLUSIVE

- TCP/DNS error to `RAMION_BASE_URL`
- `GET /api/state` fails repeatedly **and** the viewer does not load
- Viewer login/auth wall unexpected **TODO: document auth**

---

## Evidence field examples

```text
Evidence: api=measured.gripper=92,limits=[0,100]; screenshots=4
Evidence: api=n/a; screenshots=5; screenshot-only mode
Evidence: watcher=critical,rule=collision_torque,dry_run=true
```
