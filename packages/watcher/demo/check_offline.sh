#!/usr/bin/env bash
# Offline check: unit tests + scripted replay against local fake servers. No network, no robot.
set -euo pipefail
cd "$(dirname "$0")/.."
export NO_PROXY="127.0.0.1,localhost${NO_PROXY:+,$NO_PROXY}" no_proxy="127.0.0.1,localhost${no_proxy:+,$no_proxy}"
echo "== unit tests"
python3 -m unittest discover -s tests 2>&1 | tail -n 3
echo "== offline replay (-30 -> -65 -> -70 -> -40 -> -68)"
python3 demo/replay_offline.py
