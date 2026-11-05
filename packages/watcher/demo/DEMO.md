# Demo: forbidden zone `shoulder_pan < -60°`

A soft **demo zone**, not a hardware limit (the real shoulder_pan limit is -105°), so it is
safe to enter in public. The watcher only **reads** `/api/state` and camera snapshots; it never
commands the arm. The zone rule is warning-level, so it can never trigger a stop by itself.

| What happens | Intent alert |
|---|---|
| shoulder_pan goes below -60° once | `forbidden_zone` finding + `suspicious`, action `warn` |
| stays below -60° for 3 s, **or** re-enters after the warning | `bad_intent`, action `revoke_access_human_review` (a human decides in Slack) |

Alerts carry `"demo": true` and their Slack text starts with `[DEMO]`. After the `bad_intent`
alert, demo alerts stay quiet for the intent window (60 s), so you get 1–2 Slack posts.

Config: [`thresholds.demo.json`](thresholds.demo.json)

```json
{"demo_zones": [{"joint": "shoulder_pan", "below": -60, "name": "demo_left_zone"}]}
```

## Checks (run from anywhere)

```bash
# a) offline: unit tests + scripted replay (-30 -> -65 -> -70 -> -40 -> -68) on local fake servers
packages/watcher/demo/check_offline.sh

# b) live, read-only (GET only): current shoulder_pan, zone status, one dry-run cycle
RAMION_DASHBOARD_URL=http://<dashboard>:8780 packages/watcher/demo/check_live_readonly.sh

# c) Slack path: posts ONE "[DEMO] TEST" intent_alert to your webhook
PAPAJ_WEBHOOK_URL=... PAPAJ_WEBHOOK_AUTH='Bearer ...' packages/watcher/demo/send_test_alert.sh
```

## Live demo

```bash
cd packages/watcher
export RAMION_DASHBOARD_URL=http://<dashboard>:8780
export PAPAJ_WEBHOOK_URL=...            # Grok Bot routine / Slack bridge
export PAPAJ_WEBHOOK_AUTH='Bearer ...'  # optional, never logged
python3 -m papaj_watcher --config demo/thresholds.demo.json --webhook "$PAPAJ_WEBHOOK_URL"
```

Leave out `--enable-stop` (dry-run is the default). Then the **operator** takes control in the
dashboard and turns shoulder_pan left past -60° (e.g. to -70°): Slack gets a `[DEMO]` suspicious
alert. Hold it there for 3 s, or come back out and go in again, and Slack gets a `[DEMO]` bad_intent
alert asking for human review. Then return the arm to a normal pose (e.g. -10°).
