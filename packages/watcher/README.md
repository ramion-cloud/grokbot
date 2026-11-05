# Papaj Watcher

Standalone safety observer for a Ramion-style arm dashboard. It polls HTTP
routes, applies a deterministic rule layer, optionally asks a vision model
about unsafe behavior, writes warnings (stdout, JSONL, webhook), and can
request STOP on critical events.

The watcher is an external HTTP client. It does not import or copy dashboard
or controller code.

**STOP is off by default.** A dry-run logs what it would do. Enabling STOP
against a non-loopback dashboard also requires `--confirm-remote-stop`.

## Dashboard HTTP contract

Configure the base URL with `RAMION_DASHBOARD_URL` or `--url`. The placeholder
default is `http://127.0.0.1:8780`.

| Method | Path | Used by the watcher | Notes |
| --- | --- | --- | --- |
| GET | `/api/state` | Yes | JSON telemetry: joints, limits, measured/command/target, torque, speed, faults, control lease, emergency-stop latch, cameras |
| GET | `/cameras/overhead.jpg` | Yes | JPEG snapshot |
| GET | `/cameras/wrist.jpg` | Yes | JPEG snapshot |
| GET | `/cameras/observer.jpg` | Yes | JPEG snapshot |
| GET | `/cameras/{role}.mjpg` | No | Multipart stream; the watcher uses still JPEGs instead |
| GET | `/api/telemetry` | No | Some panels alias this to `/api/state`; a dashboard proxy may not expose it |
| POST | `/api/stop` | Only with `--enable-stop` | Tokenless hold: keeps torque on and revokes the operator lease |
| POST | `/api/emergency-stop` | Never | Latched e-stop; requires an explicit reset |
| POST | `/api/emergency-stop/reset` | Never | Clears a latched e-stop |
| POST | `/api/control/claim` | Never | Lease grant (`label`, `emergency_stop_generation`) |
| POST | `/api/control/heartbeat` | Never | Renews the lease (`token`) |
| POST | `/api/control/release` | Never | Drops the lease (`token`) |
| POST | `/api/target`, `/api/jog`, `/api/home`, `/api/speed`, `/api/torque` | Never | Motion commands |

The rule layer reads `/api/state` fields such as `measured`, `command`,
`target`, `limits`, optional `max_vel`, `faults`, `control.owner_id`,
`control.expires_in_s`, `emergency_stop.latched`, `age_s` / `sample.age_s`,
`connected`, `loop_ok`, and optional `temperature(s)`, `current(s)`,
`load(s)` or a nested `telemetry` object. Temperature, current, and load are
not always present; those rules stay quiet unless the payload includes them.
Velocity is derived from successive `measured` samples.

Camera roles are `overhead`, `wrist`, and `observer`.

## Install and run

Python 3.10+ and the standard library are enough.

```bash
cd packages/watcher
python3 -m unittest discover -s tests -v
```

Dry-run against a dashboard (reads only; never posts STOP):

```bash
export RAMION_DASHBOARD_URL=http://127.0.0.1:8780
python3 -m papaj_watcher \
  --interval 1.0 \
  --cameras overhead,wrist,observer \
  --log ./events.jsonl \
  --evidence ./evidence \
  --webhook "$PAPAJ_WEBHOOK_URL" \
  --config ./thresholds.example.json
```

Single cycle:

```bash
python3 -m papaj_watcher --once
```

Optional install from this directory:

```bash
pip install -e .
papaj-watcher --once
```

### Enabling STOP

```bash
python3 -m papaj_watcher --enable-stop --confirm-remote-stop
```

`--enable-stop` alone is enough only when the dashboard URL host is
`127.0.0.1`, `localhost`, or `::1` (for local fake servers and tests).
Any other host also needs `--confirm-remote-stop` or
`PAPAJ_CONFIRM_REMOTE_STOP=1`. The watcher posts `POST /api/stop` with
`Content-Type: application/json` and body `{}`. It never posts e-stop,
lease, arm, or target routes.

Do not enable STOP against a physical arm until thresholds and alert
routing are reviewed.

## Rules

Deterministic checks, evaluated every poll:

- Joint near software limits (`limits` vs `measured`)
- Velocity spikes (derived from successive samples vs `max_vel` or built-in SO-101 caps)
- Temperature / current / load spikes when those maps are present
- Collision-ish tracking error (`command` vs `measured`) and servo fault strings (English or Polish overload/overheat/overcurrent wording)
- Rapid target/command bursts
- Lease anomalies: motion without an owner, owner flicker, lease expiry while moving, stale samples, disconnects
- A latched emergency stop suppresses new STOP requests (the arm is already held)

Critical findings request STOP; warnings do not. Repeated identical findings
are cooldown-gated.

## Intent detector

`papaj_watcher/intent.py` aggregates those findings per control session
(`control.owner_id` / `control.label`) over a sliding window (default 60s)
and computes an explainable risk score.

Signals include repeated `joint_near_limits` after warnings, clipped or
out-of-limit targets, `rapid_command_bursts`, repeated `collision_torque`,
motion or re-claim right after a soft stop / lease revocation, `vision_unsafe`,
and stale-loop command changes.

Levels: `normal` (not emitted), `suspicious`, `bad_intent`. Profiles:
`novice` (isolated or decreasing after a warning) versus `deliberate`
(escalating, ignoring warnings). `recommended_action` is `warn`,
`soft_stop`, or `revoke_access_human_review`. Only recommendations — Watcher
never e-stops or revokes access. A `soft_stop` recommendation still requires
`--enable-stop` to POST `/api/stop`. Alerts use the same webhook/JSONL sinks,
with cooldown unless the level escalates. The payload includes `slack_text`
(`text` + Block Kit `blocks`) for a Grok Bot routine to post to Slack.

Disable with `--no-intent` or `PAPAJ_INTENT=0`. Tune
`PAPAJ_INTENT_WINDOW` and `PAPAJ_INTENT_COOLDOWN`.

## Optional vision layer

Set `PAPAJ_VLM_BASE_URL` to an OpenAI-compatible or local chat endpoint
(for example a local server exposing `/v1/chat/completions`). Set
`PAPAJ_VLM_API_KEY` if the provider needs a bearer token. Then pass `--vlm`.

Vision findings are warnings by default. They request STOP only when the
model returns `severity: critical` and you also pass `--vlm-can-stop`
together with `--enable-stop`.

## Alerts and evidence

- Human-readable lines on stdout
- Optional JSONL log (`--log` / `PAPAJ_LOG`)
- Optional webhook POST (`--webhook` / `PAPAJ_WEBHOOK_URL`) so a Grok Bot routine can receive the same JSON
- Evidence JPEG plus sidecar JSON under `--evidence` when a finding fires (Pillow, if installed, stamps a banner)

Webhook payload fields include `source`, `ts`, `level`, `rule`, `message`,
`details`, `should_stop`, `dry_run`, `stop_requested`, and `evidence`.

Live camera frames belong in a private evidence directory, not in git.


## Monitor integration

Papaj Watcher is the safety observer; Monitor is the exercise grader. Do not
copy these rules into Monitor.

When a finding or `intent_alert` fires, Watcher writes one JSON object to
stdout, optional JSONL (`--log` / `PAPAJ_LOG`), and optional webhook
(`--webhook` / `PAPAJ_WEBHOOK_URL`). Point that webhook at a Grok Bot routine
or Monitor intake. Rule findings use `level` (`info`, `warning`, `critical`)
and `rule` names. Intent events use `type=intent_alert` plus `slack_text`.
Monitor should treat `critical` / `bad_intent` as safety context, note
`warning` / `suspicious` in Evidence, forward intent Slack payloads to the
configured routine, and never recompute thresholds — those live in
`thresholds.example.json` and `IntentConfig`.

See `docs/architecture.md` and `bots/monitor/skills/grading-rubric/SKILL.md`.

## Configuration

| Variable / flag | Purpose |
| --- | --- |
| `RAMION_DASHBOARD_URL` / `--url` | Dashboard base URL |
| `PAPAJ_INTERVAL` / `--interval` | Poll period in seconds |
| `PAPAJ_CAMERAS` / `--cameras` | `overhead,wrist,observer` |
| `PAPAJ_TIMEOUT` / `--timeout` | HTTP timeout |
| `PAPAJ_LOG` / `--log` | JSONL path |
| `PAPAJ_EVIDENCE` / `--evidence` | Evidence directory |
| `PAPAJ_WEBHOOK_URL` / `--webhook` | Alert webhook |
| `PAPAJ_WEBHOOK_AUTH` / `--webhook-auth` | Optional `Authorization` header value sent verbatim (e.g. `Bearer xyz`); never logged |
| `PAPAJ_CONFIG` / `--config` | Thresholds JSON |
| `PAPAJ_THRESHOLDS_JSON` | Inline thresholds JSON |
| `PAPAJ_ENABLE_STOP` / `--enable-stop` | Allow `POST /api/stop` |
| `PAPAJ_CONFIRM_REMOTE_STOP` / `--confirm-remote-stop` | Required for STOP against non-loopback URLs |
| `PAPAJ_VLM_ENABLED` / `--vlm` | Enable vision |
| `PAPAJ_VLM_BASE_URL` / `--vlm-base-url` | VLM endpoint |
| `PAPAJ_VLM_API_KEY` | VLM bearer token |
| `PAPAJ_VLM_MODEL` / `--vlm-model` | Model name |
| `PAPAJ_VLM_CAN_STOP` / `--vlm-can-stop` | Let critical VLM findings request STOP |
| `PAPAJ_INTENT` / `--no-intent` | Intent detector (default on; `--no-intent` or `PAPAJ_INTENT=0` disables) |
| `PAPAJ_INTENT_WINDOW` / `--intent-window` | Sliding window in seconds (default 60) |
| `PAPAJ_INTENT_COOLDOWN` / `--intent-cooldown` | Intent alert cooldown in seconds (default 30) |

See `thresholds.example.json` and `deploy/papaj-watcher.env.example`.

## systemd

`deploy/papaj-watcher.service` is an example unit. Copy
`deploy/papaj-watcher.env.example` to a private env file, point
`WorkingDirectory` at this package, and leave `PAPAJ_ENABLE_STOP=0`
until you are ready.

## Tests

Fixtures under `tests/fixtures/` are synthetic (a generated JPEG and hand-written state JSON). They are not live captures.

```bash
python3 -m unittest discover -s tests -v
```

## Decisions you still need to make

- Which dashboard URL to set in the private env file
- Whether a VLM is used, which endpoint/model, and where the API key lives
- Warning vs critical thresholds for your hardware
- Who receives webhook alerts (a team channel, a Grok Bot routine, both)
- Whether STOP may ever be enabled on a physical arm, and who is allowed to set that flag
