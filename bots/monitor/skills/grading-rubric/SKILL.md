---
name: ramion-grading-rubric
description: >-
  Pass/fail criteria for Ramion hands-on exercises using API state and viewer screenshots.
---

# Grading rubrics

Default **timeout:** 60s from Tutor grade request.  
Default **stable samples:** 2 consecutive observations meeting pass condition, sampled every 2–3s.

Use proposed `GET /api/v1/state` when HTTP 200; else screenshot-only mode.

Report using Monitor output format in `bots/monitor/PERSONA.md`.

---

## `open-gripper`

| Mode | Pass | Fail |
|------|------|------|
| API | `gripper.open === true` and `motion.busy === false` | `gripper.open === false` at timeout |
| Screenshot | UI shows open state (label “Open”, separated fingers, or open icon) | Closed or ambiguous at timeout |

**Notes:**

- If `gripper.position_normalized` exists: pass if `>= 0.85` **TODO: calibrate on real server**.
- If `safety.soft_stopped === true` mid-exercise → FAIL `unexpected soft stop`.

---

## `close-gripper`

| Mode | Pass | Fail |
|------|------|------|
| API | `gripper.open === false` and `motion.busy === false` | Still open at timeout |
| Screenshot | Closed icon / “Closed” label | Open at timeout |

**Normalized fallback:** `position_normalized <= 0.15` **TODO: calibrate**.

---

## `move-home`

| Mode | Pass | Fail |
|------|------|------|
| API | `motion.busy === false` and joints within tolerance of preset **TODO: define home vector** | Busy at timeout or joints far from home |
| Screenshot | Arm depicted at home/ready pose matching UI legend | Clearly not at home |

**Interim API heuristic (until home vector TODO):**

- Pass if `motion.last_command` contains `home` or `preset` and `motion.busy === false` after command window.

---

## Global FAIL reasons (any exercise)

| Reason code | When |
|-------------|------|
| `timeout` | No stable pass within timeout |
| `state mismatch` | API and screenshot disagree |
| `disconnected` | `connected === false` in API |
| `inconclusive` | Cannot load viewer or API unreachable |

---

## Global INCONCLUSIVE

- TCP/DNS error to `RAMION_BASE_URL`
- Health check fails 5 times in a row
- Viewer login/auth wall unexpected **TODO: document auth**

---

## Evidence field examples

```text
Evidence: api=gripper.open=true,motion.busy=false; screenshots=4
Evidence: api=n/a (404); screenshots=5; screenshot-only mode
```
