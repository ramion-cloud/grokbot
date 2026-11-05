#!/usr/bin/env bash
# Post ONE sample intent_alert ("[DEMO] TEST") to your webhook to verify the Slack path before the demo.
# Talks only to $PAPAJ_WEBHOOK_URL; never contacts the robot.
set -euo pipefail
: "${PAPAJ_WEBHOOK_URL:?set PAPAJ_WEBHOOK_URL}"
python3 - <<'PY'
import json, os, time, urllib.request
text = "[DEMO] TEST Papaj Watcher intent: suspicious (score 5.0) - shoulder_pan -65.0° is below demo limit -60°"
payload = {
    "type": "intent_alert", "source": "papaj-watcher", "demo": True, "dry_run": True,
    "ts_epoch": time.time(), "level": "suspicious", "score": 5.0, "profile": "benign",
    "session": {"owner_id": None, "label": "demo-test"},
    "reasons": [{"code": "forbidden_zone", "detail": "shoulder_pan -65.0° is below demo limit -60°", "weight": 5.0}],
    "recommended_action": "warn",
    "slack_text": {"text": text, "blocks": [
        {"type": "header", "text": {"type": "plain_text", "text": "[DEMO] TEST intent alert"}},
        {"type": "section", "text": {"type": "mrkdwn", "text": text}}]},
    "text": text,
}
headers = {"Content-Type": "application/json", "User-Agent": "papaj-watcher/0.1"}
if os.environ.get("PAPAJ_WEBHOOK_AUTH"):
    headers["Authorization"] = os.environ["PAPAJ_WEBHOOK_AUTH"]
req = urllib.request.Request(os.environ["PAPAJ_WEBHOOK_URL"], data=json.dumps(payload).encode(), headers=headers, method="POST")
with urllib.request.urlopen(req, timeout=10) as r:
    print("webhook responded", r.status)
PY
