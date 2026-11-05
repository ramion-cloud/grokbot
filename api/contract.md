# Ramion dashboard HTTP contract

**Base URL:** set `RAMION_BASE_URL` (Monitor/Tutor) or `RAMION_DASHBOARD_URL` (Papaj Watcher) in a private environment. Do not commit hostnames, addresses, or tokens.

> **Status:** Routes and fields marked **verified** match the live dashboard/panel contract used by Papaj Watcher. Items marked **proposed** were part of the original scaffold and are **not** verified on the live server — do not call them unless a later inventory confirms them.

## Conventions

- JSON request/response bodies unless noted (`image/jpeg` for snapshots).
- Errors are typically `{ "error": "…" }` with an appropriate HTTP status.
- Auth: tailnet or other private reachability is configured outside this repo. **TODO** if a bearer token is added later.
- Soft-stop is `POST /api/stop`. It is not a hardware e-stop.

---

## Verified routes

### `GET /api/state` — **verified**

**Purpose:** Single telemetry snapshot for Watcher rules, Monitor grading, and Tutor status.

**Response 200** (`application/json`). Verified top-level fields:

```json
{
  "robot": "so101",
  "joints": ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"],
  "limits": {
    "shoulder_pan": [-105.0, 105.0],
    "gripper": [0.0, 100.0]
  },
  "measured": {
    "shoulder_pan": 0.0,
    "gripper": 35.0
  },
  "command": {
    "shoulder_pan": 0.0,
    "gripper": 35.0
  },
  "target": {
    "shoulder_pan": 0.0,
    "gripper": 35.0
  },
  "torque": true,
  "speed": 30.0,
  "clip": null,
  "faults": [],
  "loop_hz": 20,
  "age_s": 0.04,
  "sequence": 12,
  "loop_ok": true,
  "connected": true,
  "control": {
    "owner_id": null,
    "label": null,
    "expires_in_s": 0.0
  },
  "sample": {
    "age_s": 0.04,
    "sequence": 12,
    "loop_ok": true,
    "connected": true
  },
  "events": [],
  "emergency_stop": {
    "latched": false,
    "generation": 0,
    "hold_status": "not_requested",
    "hold_error": null
  },
  "cameras": {
    "overhead": {"status": "live", "age_s": 0.12, "url": "/cameras/overhead.mjpg", "error": null},
    "wrist": {"status": "live", "age_s": 0.11, "url": "/cameras/wrist.mjpg", "error": null},
    "observer": {"status": "live", "age_s": 0.13, "url": "/cameras/observer.mjpg", "error": null}
  }
}
```

**Field notes:**

| Field | Meaning |
|-------|---------|
| `robot` | Robot name string |
| `joints` | **List of joint names** (not a map of angles) |
| `limits` | Per-joint `[low, high]` |
| `measured` | Latest measured pose, keyed by joint name |
| `command` | Last command sent to the servos |
| `target` | Operator/controller target pose |
| `torque` | Whether torque is enabled |
| `speed` | Panel speed cap |
| `clip` | Null, or a message when a target was clipped to a limit |
| `faults` | List of servo/link fault strings (English or Polish wording may appear) |
| `loop_hz` | Recent control-loop tick rate |
| `age_s` | Age of the latest joint sample, seconds |
| `sequence` | Monotonic sample counter |
| `loop_ok` | Control loop healthy |
| `connected` | Arm link connected |
| `control.owner_id` | Lease owner, or null if nobody holds control |
| `control.label` | Operator label for the lease |
| `control.expires_in_s` | Seconds until the heartbeat lease expires |
| `sample` | Mirror of freshness fields (`age_s`, `sequence`, `loop_ok`, `connected`) |
| `events` | Recent controller events (`timestamp`, `level`, `message`) |
| `emergency_stop` | Latch object (`latched`, `generation`, `hold_status`, `hold_error`) |
| `cameras` | Per-role camera status (`overhead`, `wrist`, `observer`) |

There is no verified `gripper.open` boolean, `motion.busy`, or `safety.soft_stopped` object. Use `state.gripper` when present as the gripper **joint name**, then read `measured[gripper]`, `target[gripper]`, and `limits[gripper]`. Infer “still moving” when any `|target[j] - measured[j]|` exceeds `motion_epsilon_deg` from [`packages/watcher/thresholds.example.json`](../packages/watcher/thresholds.example.json) (default `1.5`). Treat `emergency_stop.latched === true` as a software stop already held.

Optional maps such as `temperature(s)`, `current(s)`, `load(s)`, `max_vel`, or a nested `telemetry` object may appear; Watcher rules use them when present and stay quiet otherwise.

### `GET /cameras/{overhead,wrist,observer}.jpg` — **verified**

**Purpose:** Still JPEG snapshot for a named camera role.

**Response 200:** `image/jpeg`. Missing or stale frames may return a non-200 (for example `503`) with a JSON error.

Papaj Watcher polls these paths. Multipart `/cameras/{role}.mjpg` streams exist on some dashboards; Watcher does not subscribe to them.

### `POST /api/stop` — **verified** (soft stop)

**Purpose:** Software hold. Keeps torque on so the arm does not drop, sets target/command to the measured pose, and revokes the operator lease. **Not** a hardware e-stop and **not** a latched emergency-stop.

**Request:** `Content-Type: application/json` and body `{}`. No control token is required.

**Who may call it:**

- Papaj Watcher, only when `--enable-stop` is set (default **off** / dry-run). Non-loopback URLs also require `--confirm-remote-stop`.
- Tutor, once per incident, when the learner asks to stop or a Watcher `critical` alert is forwarded.

Do not call latched emergency-stop routes from bots.

---

## Watcher alert contract — **verified** (Papaj Watcher output)

Watcher writes the same JSON object to stdout, an optional JSONL log (`PAPAJ_LOG`), and an optional webhook (`PAPAJ_WEBHOOK_URL`):

```json
{
  "source": "papaj-watcher",
  "ts": "2026-11-05T19:00:00+01:00",
  "ts_epoch": 1762365600.0,
  "level": "warning",
  "rule": "joint_near_limits",
  "message": "shoulder_pan is 7.0 deg from its limit",
  "details": {},
  "should_stop": false,
  "dry_run": true,
  "stop_requested": false,
  "evidence": []
}
```

**Severity levels:** `info` | `warning` | `critical`.

**Rule names** (do not rename in Monitor; do not reimplement the heuristics):

| `rule` | Typical meaning |
|--------|-----------------|
| `joint_near_limits` | Measured pose close to `limits` |
| `velocity_spike` | Derived velocity vs `max_vel` / default caps |
| `temperature_spike` | Temperature map present and high |
| `current_spike` | Current map present and high |
| `collision_torque` | Tracking error, load spike, or servo fault |
| `rapid_command_bursts` | Many target/command changes in a short window |
| `lease_anomaly` | Motion without a lease, owner flicker, expiry while moving, stale sample, disconnect |
| `vision_unsafe` | Optional VLM finding |

`should_stop` is true for `critical` findings unless `emergency_stop.latched` is already true. Thresholds live in [`packages/watcher/thresholds.example.json`](../packages/watcher/thresholds.example.json). Monitor consumes these alerts; it does not duplicate the rule engine.

---


## Intent alert contract — **verified** (Papaj Watcher intent detector)

Watcher aggregates per-session findings (`control.owner_id` / `control.label`) over a sliding window and may emit a second JSON object to the same JSONL log and webhook. `type` is `intent_alert`. Levels are `normal` (not emitted), `suspicious`, and `bad_intent`. `recommended_action` is `warn` | `soft_stop` | `revoke_access_human_review`. Soft-stop remains gated by `--enable-stop`. Watcher never e-stops and never revokes access itself.

```json
{
  "type": "intent_alert",
  "source": "papaj-watcher",
  "ts": "2026-11-05T20:15:00+01:00",
  "ts_epoch": 1762370100.0,
  "level": "bad_intent",
  "score": 18.5,
  "session": {"owner_id": "owner-fixture", "label": "fixture-operator"},
  "profile": "deliberate",
  "reasons": [
    {
      "code": "repeated_joint_near_limits_after_warning",
      "detail": "Repeated joint_near_limits after an earlier warning",
      "weight": 3.0
    },
    {
      "code": "collision_torque_repeats",
      "detail": "collision_torque fired 2 times in the window",
      "weight": 2.0
    }
  ],
  "evidence": ["/var/lib/papaj-watcher/evidence/sim-frame.jpg"],
  "recommended_action": "revoke_access_human_review",
  "dry_run": true,
  "slack_text": {
    "text": "Papaj Watcher intent: bad_intent (score 18.5)\nSession: fixture-operator\nProfile: deliberate\nRecommended action: revoke_access_human_review (dry_run=true)\nReasons:\n- Repeated joint_near_limits after an earlier warning\nHuman review is required to revoke access. Watcher never e-stops or revokes automatically.",
    "blocks": [
      {
        "type": "header",
        "text": {"type": "plain_text", "text": "Intent bad_intent (score 18.5)", "emoji": true}
      },
      {
        "type": "section",
        "fields": [
          {"type": "mrkdwn", "text": "*Session:*\nfixture-operator"},
          {"type": "mrkdwn", "text": "*Profile:*\ndeliberate"},
          {"type": "mrkdwn", "text": "*Action:*\n`revoke_access_human_review`"},
          {"type": "mrkdwn", "text": "*Dry-run:*\ntrue"}
        ]
      },
      {"type": "section", "text": {"type": "mrkdwn", "text": "*Reasons:*\n• Repeated joint_near_limits after an earlier warning"}},
      {
        "type": "context",
        "elements": [
          {
            "type": "mrkdwn",
            "text": "Recommended action only. Soft-stop is gated by `--enable-stop`. Never e-stop or revoke access automatically — a human decides."
          }
        ]
      }
    ]
  }
}
```

`profile` is `benign`, `novice` (isolated or decreasing after warnings), or `deliberate` (escalating, ignoring warnings, motion/reclaim after stop, or repeated collision/vision signals). Dedup/cooldown applies unless the level escalates or the score jumps.

Monitor and a Grok Bot routine should POST `slack_text` (plain `text` plus Block Kit `blocks`) to Slack. A human reviews `revoke_access_human_review`.

## Proposed routes (not verified)

The paths below were drafted in the original scaffold. They are **not** verified on the live dashboard. Prefer the verified routes above.

| Proposed path | Live substitute |
|---------------|-----------------|
| `GET /api/v1/state` | `GET /api/state` |
| `GET /api/v1/health` | `GET /api/state` (HTTP 200 means the dashboard answered) |
| `POST /api/v1/control/soft-stop` | `POST /api/stop` |
| `POST /api/v1/gripper` | Learner uses the viewer; bots should not drive motion |
| `POST /api/v1/motion/preset` | Learner uses the viewer; bots should not drive motion |

### `GET /` *(dashboard HTML)*

Live teleoperation viewer / panel page. Monitor may open `${RAMION_BASE_URL}/` for screenshots. Exact chrome and controls are UI details, not part of the verified JSON contract.

---

## Mapping to exercises

| Exercise ID | Primary pass condition (`GET /api/state`) | Screenshot fallback |
|-------------|-------------------------------|---------------------|
| `open-gripper` | Gripper joint `measured` value `>= low + 0.85 * (high - low)` and not still moving | UI shows open / separated fingers |
| `close-gripper` | Gripper joint `measured` value `<= low + 0.15 * (high - low)` and not still moving | UI shows closed |
| `move-home` | `connected` and not still moving; screenshot or operator-defined home pose (live state has no home vector field) | Arm depicted at the UI home/ready pose |

See `bots/monitor/skills/grading-rubric/SKILL.md`.

---

## Integration checklist

- [x] Document verified `GET /api/state` fields, camera JPEGs, and `POST /api/stop`.
- [x] Point Monitor/Tutor skills at those routes instead of unverified `/api/v1/…` paths.
- [x] Document Watcher webhook/JSONL alert names and levels.
- [x] Document `intent_alert` schema and Slack `slack_text` payload.
- [ ] Set private env `RAMION_BASE_URL` / `RAMION_DASHBOARD_URL` / `RAMION_VIEWER_URL` per deployment.
- [ ] Point `PAPAJ_WEBHOOK_URL` at the Monitor / ops intake if Watcher should notify the teaching loop.
