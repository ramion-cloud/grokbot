---
name: ramion-observe-session
description: >-
  How Monitor reaches the Ramion viewer, polls GET /api/state, captures
  screenshots, and reads Papaj Watcher alerts.
---

# Observe session

## Prerequisites (operator)

1. Grok Bot environment that can reach the dashboard (`RAMION_BASE_URL`).
2. Env var `RAMION_BASE_URL` with no trailing slash (private; do not commit hostnames).
3. Browser or HTTP tools enabled for Monitor agent.
4. Optional: Papaj Watcher webhook or JSONL path so Monitor can read safety alerts without running the rule engine.

## Step 0 — Parse grade request

From Tutor message extract:

- `exercise-id` (required): `open-gripper` | `close-gripper` | `move-home`
- `timeout_sec` (optional, default 60)

## Step 1 — Reachability

```http
GET ${RAMION_BASE_URL}/api/state
```

- **200 + JSON:** continue with API + screenshots.
- **404 / connection error:** log `API state unavailable`; proceed screenshot-only if viewer loads.

Do not call unverified `GET /api/v1/health` or `GET /api/v1/state`.

## Step 2 — Open viewer

Navigate browser to:

```text
${RAMION_BASE_URL}/
```

Wait for primary viewer canvas/controls (timeout 15s page load).

## Step 3 — Observation loop

Until `timeout_sec` elapsed:

| Tick | Action |
|------|--------|
| Every 2–3s | Full-page or viewer-region screenshot (consistent crop across ticks) |
| Same tick | `GET ${RAMION_BASE_URL}/api/state` if step 1 succeeded |
| Same tick | Read any new Papaj Watcher JSON (`source=papaj-watcher`) from webhook inbox or JSONL tail |
| After each tick | Evaluate the **exercise** rubric; if a Watcher event has `level=critical`, FAIL using that `rule` name |

Stop early when consecutive pass samples ≥ 2 and no Watcher `critical` is pending.

## Step 4 — Screenshot-only fallback

When API unavailable:

- Do **not** invent JSON state.
- Apply screenshot columns in `grading-rubric/SKILL.md` only.
- Mention `screenshot-only mode` in Evidence.
- Still honor Watcher webhook/JSONL alerts if they arrive.

## Step 5 — Return result to Tutor

Post structured message (see PERSONA). Example:

```text
[open-gripper] RESULT: PASS
Reason: measured gripper near open limit for 2 consecutive API samples; viewer shows open.
Evidence: api=measured.gripper=92,limits=[0,100]; screenshots=3
```

## Cadence vs RTSP

Do **not** subscribe to RTSP for hackathon grading. Sequential screenshots match learner UI and keep Monitor simple. Papaj Watcher polls still JPEGs (`/cameras/{role}.jpg`) separately.

## Security

- Do not exfiltrate screenshots outside grading thread.
- Do not store credentials or private hostnames in chat.

## Troubleshooting

| Issue | Action |
|-------|--------|
| `RAMION_BASE_URL` unreachable | INCONCLUSIVE; fix agent network |
| Blank screenshot | INCONCLUSIVE; suggest learner reload viewer |
| `emergency_stop.latched` | FAIL `unexpected stop`; Tutor handles ops |
| Watcher `critical` | FAIL with Watcher `rule`; do not recompute the heuristic |
