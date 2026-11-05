---
name: ramion-observe-session
description: >-
  How Monitor reaches the Ramion viewer, polls API, and captures screenshot cadence.
---

# Observe session

## Prerequisites (operator)

1. Grok Bot environment on **Tailscale** with access to `ramion-server-01.tail0fbdb0.ts.net`.
2. Env var `RAMION_BASE_URL=http://ramion-server-01.tail0fbdb0.ts.net:8780` (no trailing slash).
3. Browser or HTTP tools enabled for Monitor agent.

## Step 0 — Parse grade request

From Tutor message extract:

- `exercise-id` (required): `open-gripper` | `close-gripper` | `move-home`
- `timeout_sec` (optional, default 60)

## Step 1 — Health check (proposed)

```http
GET ${RAMION_BASE_URL}/api/v1/health
```

- **200 + ok:** continue.
- **404 / connection error:** log `API health unavailable`; proceed screenshot-only if viewer loads.

## Step 2 — Open viewer

Navigate browser to:

```text
${RAMION_BASE_URL}/
```

Wait for primary viewer canvas/controls (timeout 15s page load).

**TODO:** If viewer path is not `/`, update to match server.

## Step 3 — Observation loop

Until `timeout_sec` elapsed:

| Tick | Action |
|------|--------|
| Every 2–3s | Full-page or viewer-region screenshot (consistent crop across ticks) |
| Same tick | `GET ${RAMION_BASE_URL}/api/v1/state` if health succeeded earlier |
| After each tick | Evaluate rubric for `exercise-id`; count consecutive pass samples |

Stop early when consecutive pass samples ≥ 2.

## Step 4 — Screenshot-only fallback

When API unavailable:

- Do **not** invent JSON state.
- Apply screenshot columns in `grading-rubric/SKILL.md` only.
- Mention `screenshot-only mode` in Evidence.

## Step 5 — Return result to Tutor

Post structured message (see PERSONA). Example:

```text
[open-gripper] RESULT: PASS
Reason: gripper.open true for 2 consecutive API samples; viewer shows open.
Evidence: api=gripper.open=true,motion.busy=false; screenshots=3
```

## Cadence vs RTSP

Do **not** subscribe to RTSP for hackathon grading. Sequential screenshots match learner UI and keep Monitor simple. Watcher may use higher-rate video separately.

## Security

- Do not exfiltrate screenshots outside grading thread.
- Do not store tailnet credentials in chat.

## Troubleshooting

| Issue | Action |
|-------|--------|
| MagicDNS fails, short name works from learner | Fix Monitor Tailscale DNS; always use MagicDNS in env |
| Blank screenshot | INCONCLUSIVE; suggest learner reload viewer |
| Soft-stop latched | FAIL with reason; Tutor handles ops |
