#!/usr/bin/env bash
# Read-only live check: GET /api/state, report shoulder_pan vs the demo zone, then one dry-run watcher cycle.
# Sends GET requests only. Never stops, moves or leases the arm. Honours HTTP_PROXY if set.
set -euo pipefail
cd "$(dirname "$0")/.."
: "${RAMION_DASHBOARD_URL:?set RAMION_DASHBOARD_URL to the dashboard base URL}"
python3 - <<'PY'
import json, os, urllib.request
base = os.environ["RAMION_DASHBOARD_URL"].rstrip("/")
zones = json.load(open("demo/thresholds.demo.json"))["demo_zones"]
with urllib.request.urlopen(base + "/api/state", timeout=8) as r:
    state = json.load(r)
for z in zones:
    pos = (state.get("measured") or {}).get(z["joint"])
    inside = pos is not None and pos < z["below"]
    print(f"{z['joint']} = {pos:.1f}°  (demo zone: < {z['below']}°)  ->  {'IN ZONE' if inside else 'outside zone'}")
print(f"loop_hz={state.get('loop_hz')} faults={len(state.get('faults') or [])}")
PY
unset PAPAJ_ENABLE_STOP PAPAJ_WEBHOOK_URL PAPAJ_WEBHOOK_AUTH
echo "== one dry-run watcher cycle with demo thresholds"
python3 -m papaj_watcher --once --url "$RAMION_DASHBOARD_URL" --config demo/thresholds.demo.json
