# grokbot

Public home for Grok Bot roles that work with a Ramion-style arm dashboard
over HTTP. Each role is a sibling package under `packages/`. Packages talk
to the dashboard as external clients; they do not vendor dashboard or
controller source.

| Package | Role |
| --- | --- |
| [`packages/watcher`](packages/watcher) | Papaj Watcher — poll camera snapshots and joint/state telemetry, emit team warnings, and optionally request STOP |
| `packages/onboarding` | Reserved for a future onboarding role |
| `packages/training` | Reserved for a future training role |

Only the watcher is implemented today. Add later roles next to it, with
their own README, tests, and config via environment variables.

Do not put private hostnames, addresses, tokens, personal information, or
live camera frames in this repository. Configure deployments through env
files that stay off git.

## Watcher quick start

```bash
cd packages/watcher
python3 -m unittest discover -s tests -v
export RAMION_DASHBOARD_URL=http://127.0.0.1:8780
python3 -m papaj_watcher --once
```

See [`packages/watcher/README.md`](packages/watcher/README.md) for routes,
safety flags, webhooks, the optional VLM layer, and a systemd example.
