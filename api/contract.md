# Ramion server HTTP contract (proposed)

**Base URL (tailnet):**

- Short: `http://ramion-server-01:8780`
- MagicDNS: `http://ramion-server-01.tail0fbdb0.ts.net:8780`

> **Status:** Endpoints below are **proposed** for alignment between the live app at `:8780`, Tutor/Monitor skills, and the robot stack. They are **not** verified as implemented in this empty scaffold repo. Mark server-side gaps as **TODO** during integration.

## Conventions

- JSON request/response bodies unless noted.
- Errors: `{ "error": "code", "message": "human readable" }` with appropriate HTTP status.
- Auth: **TODO** — document whether tailnet membership is sufficient or if `Authorization: Bearer …` is required.

---

## Viewer (HTML)

### `GET /`

**Purpose:** Live teleoperation viewer (learner UI).

**Response:** `text/html` — interactive page with arm visualization and gripper controls.

**Monitor usage:** Navigate with browser tool; capture screenshots on cadence.

**TODO:** Confirm exact path if viewer is mounted at `/viewer` instead of `/`.

---

## Read state

### `GET /api/v1/state` *(proposed)*

**Purpose:** Single snapshot for Monitor grading and Tutor status messages.

**Response 200 (example):**

```json
{
  "connected": true,
  "session_id": "abc123",
  "joints": {
    "j1": 0.0,
    "j2": -0.5,
    "j3": 1.2,
    "j4": 0.0,
    "j5": 0.0,
    "j6": 0.0
  },
  "joint_units": "rad",
  "gripper": {
    "open": true,
    "position_normalized": 1.0
  },
  "motion": {
    "busy": false,
    "last_command": "gripper_open"
  },
  "safety": {
    "soft_stopped": false,
    "estop_latched": false
  }
}
```

**Field notes:**

| Field | Use in grading |
|-------|----------------|
| `gripper.open` | Primary signal for open/close exercises |
| `gripper.position_normalized` | Fallback if boolean ambiguous (threshold **TODO**) |
| `motion.busy` | Wait until false before final grade |
| `safety.soft_stopped` | Fail active exercise if true unexpectedly |

**TODO:** Confirm joint count/names on real arm.  
**TODO:** Confirm whether `estop_latched` is exposed to API or hardware-only.

---

## Commands *(proposed — server may already expose via UI only)*

### `POST /api/v1/gripper`

**Body:**

```json
{ "action": "open" }
```

or

```json
{ "action": "close" }
```

**Response 202:**

```json
{ "accepted": true, "command_id": "cmd-789" }
```

**TODO:** Whether Tutor/learner may call this or UI-only. Bots should **not** drive motion for hackathon grading except via learner in viewer unless explicitly allowed.

### `POST /api/v1/motion/preset` *(proposed)*

**Body:**

```json
{ "preset": "home" }
```

**Response 202:** `{ "accepted": true, "command_id": "cmd-790" }`

**TODO:** List valid preset names on real server (`home`, `ready`, etc.).

---

## Soft stop (bot-safe)

### `POST /api/v1/control/soft-stop` *(proposed)*

**Purpose:** Software motion halt + session freeze. **Not** a substitute for hardware e-stop.

**Body (optional):**

```json
{ "reason": "learner_requested", "source": "tutor_bot" }
```

**Response 200:**

```json
{ "soft_stopped": true, "message": "Motion disabled until ops reset" }
```

**TODO:** Confirm reset procedure (`POST /api/v1/control/reset-soft-stop`?) and ops-only auth.

---

## Health

### `GET /api/v1/health` *(proposed)*

**Response 200:**

```json
{ "ok": true, "version": "0.0.0" }
```

Monitor may call before grading to avoid false `FAIL`.

---

## Discord ops hook *(optional, out of band)*

Not part of `:8780` necessarily — Tutor may POST to a Discord webhook when soft-stop fires.

**TODO:** Document webhook env var name on Grok Bot deployment (`DISCORD_OPS_WEBHOOK_SECRET_NAME`).

---

## Mapping to exercises

| Exercise ID | Primary pass condition (API) | Screenshot fallback |
|-------------|-------------------------------|---------------------|
| `open-gripper` | `gripper.open === true` | UI shows “Open” / fingers separated |
| `close-gripper` | `gripper.open === false` | UI shows “Closed” |
| `move-home` | Joints within **TODO** tolerance of `home` preset | Arm icon at home pose |

See `bots/monitor/skills/grading-rubric/SKILL.md` for thresholds and timeouts.

---

## Integration checklist (team)

- [ ] Inventory actual routes on `ramion-server-01:8780` (curl + browser devtools).
- [ ] Update this file; remove *(proposed)* labels for implemented routes.
- [ ] Set Monitor env `RAMION_BASE_URL` to MagicDNS base.
- [ ] Document auth if added.
- [ ] Verify soft-stop does not conflict with hardware e-stop semantics.
