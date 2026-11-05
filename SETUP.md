# Setup — Ramion Tutor + Monitor on Grok Bot

Step-by-step to reproduce the hackathon multi-agent loop. No secrets belong in this repo — configure them in Grok Bot / Tailscale consoles.

## Prerequisites

- GitHub repo: https://github.com/ramion-cloud/grokbot (clone locally or open in Cursor).
- Access to the Ramion dashboard (set `RAMION_BASE_URL` privately).
- Two Grok Bot agent slots (Tutor + Monitor) and a **group channel** that includes both bots and the learner.
- Optional: Discord server + incoming webhook for soft-stop alerts.

## 1. Clone and attach repo to bots

```bash
git clone https://github.com/ramion-cloud/grokbot.git
cd grokbot
```

When creating each Grok Bot agent, connect this repository so skills and personas load from:

- `bots/tutor/PERSONA.md` + `bots/tutor/skills/**`
- `bots/monitor/PERSONA.md` + `bots/monitor/skills/**`

Exact UI labels may read **Agent**, **Bot**, or **Template** — attach the same repo to both.

## 2. Create Tutor bot

1. New Grok Bot agent → name e.g. `ramion-tutor`.
2. Set system instructions: paste or reference `bots/tutor/PERSONA.md`.
3. Enable skills from repo paths:
   - `bots/tutor/skills/curriculum-intro/SKILL.md`
   - `bots/tutor/skills/quiz-gate/SKILL.md`
   - `bots/tutor/skills/exercise-script/SKILL.md`
4. Environment variables (no secrets in git):

   | Variable | Example value |
   |----------|-----------------|
   | `RAMION_VIEWER_URL` | dashboard viewer URL (private env; do not commit hostnames) |

5. Optional: Discord ops webhook via platform **secret name** (e.g. `DISCORD_OPS_WEBHOOK`) — Tutor posts after soft-stop.

## 3. Create Monitor bot

1. New Grok Bot agent → name e.g. `ramion-monitor`.
2. System instructions: `bots/monitor/PERSONA.md`.
3. Skills:
   - `bots/monitor/skills/grading-rubric/SKILL.md`
   - `bots/monitor/skills/observe-session/SKILL.md`
4. Enable **HTTP** and **browser/screenshot** tools (names vary by Grok Bot version).
5. Environment:

   | Variable | Value |
   |----------|--------|
   | `RAMION_BASE_URL` | dashboard base URL, no trailing slash (private env) |

## 4. Connect Tailscale for Monitor

Monitor must reach the private viewer from the agent runtime.

**Team tailnet (recommended for Ramion org):**

1. Cursor team admin enables Tailscale for Grok Bot (company tailnet).
2. Member authenticates device; admin applies posture limiting bot egress if required.
3. Confirm from agent shell or diagnostic: `GET ${RAMION_BASE_URL}/api/state` or viewer `/`.

**Personal tailnet alternative:** If the arm server is on a personal tailnet, use one-click Connect when you administer that tailnet; otherwise ask an admin to tag a `grokbot` device.

See Cursor Tailscale docs in product help — do not commit auth keys.

**Verify:**

```bash
curl -sS -o /dev/null -w "%{http_code}" "${RAMION_BASE_URL}/api/state"
```

Expect `200`. Non-zero exit → fix reachability before demo.

## 5. Create group channel

1. Grok Bot → **Channels** → create **group** channel e.g. `ramion-lab`.
2. Add participants:
   - Learner user(s)
   - `ramion-tutor`
   - `ramion-monitor`
3. Document invocation pattern for Tutor → Monitor, e.g.:
   - Mention `@ramion-monitor grade exercise-id=open-gripper`
   - Or channel tool “request monitor grade” if configured

Both bots must see the same thread for PASS/FAIL visibility.

## 6. API contract

`api/contract.md` documents **verified** live routes (`GET /api/state`, camera JPEGs, `POST /api/stop`) and leftover **proposed** `/api/v1/…` paths that should not be used against the dashboard. Exercise rubrics read the verified fields. Safety thresholds live in `packages/watcher/thresholds.example.json` — do not fork a second copy in Monitor.

## 7. Share Tutor as Template

1. Grok Bot → Tutor agent → **Share as Template** (or equivalent).
2. Description: “Ramion hackathon — quiz-gated remote arm lab with Monitor grading.”
3. Include link to this repo and `SETUP.md`.
4. Keep Monitor as separate template or private ops agent if you prefer not to fork grading.

## 8. Discord ops (optional)

1. Create `#ramion-ops` channel; create incoming webhook.
2. Store webhook URL as deployment secret.
3. Tutor PERSONA: on soft-stop, post `{ "content": "Ramion soft-stop triggered by tutor", ... }`.

Monitor does not need Discord unless team policy says otherwise.

## 9. Dry run (5 minutes)

| Step | Actor |
|------|--------|
| Learner says “start” | Tutor runs intro + quiz |
| Intentionally fail one quiz question | Tutor withholds URL |
| Pass quiz | Tutor posts `RAMION_VIEWER_URL` |
| Exercise 1 | Learner opens gripper; Tutor pings Monitor |
| Monitor | PASS/FAIL visible in channel |

Use `demo/CHECKLIST.md` for judge timing.

## 10. Papaj Watcher (`packages/watcher`)

Watcher is implemented in this repo. It is an HTTP client of the dashboard, not a copy of the robot stack.

```bash
cd packages/watcher
python3 -m unittest discover -s tests -v
export RAMION_DASHBOARD_URL="$RAMION_BASE_URL"
# Optional: point alerts at Monitor / a Grok Bot routine
export PAPAJ_WEBHOOK_URL="$MONITOR_ALERT_WEBHOOK"
export PAPAJ_LOG=./events.jsonl
export PAPAJ_EVIDENCE=./evidence
python3 -m papaj_watcher
```

Leave `PAPAJ_ENABLE_STOP` unset (dry-run). Monitor consumes each JSON object (`source`, `level`, `rule`, `message`, `should_stop`, `dry_run`) from the webhook or JSONL file and must not re-run those rules. See `packages/watcher/README.md` and `docs/architecture.md`.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Monitor INCONCLUSIVE | Tailscale on agent; check `RAMION_BASE_URL` |
| Tutor shares URL early | Re-import quiz-gate skill; reinforce PERSONA |
| `GET /api/state` unavailable | Screenshot-only grading; note `screenshot-only mode` |
| Learner off tailnet | Join tailnet before quiz pass |

## References

- Architecture: `docs/architecture.md`
- API: `api/contract.md`
- Watcher: `packages/watcher/README.md`
- Demo: `demo/CHECKLIST.md`
