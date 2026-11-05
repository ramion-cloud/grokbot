# Setup — Ramion Tutor + Monitor on Grok Bot

Step-by-step to reproduce the hackathon multi-agent loop. No secrets belong in this repo — configure them in Grok Bot / Tailscale consoles.

## Prerequisites

- GitHub repo: https://github.com/ramion-cloud/grokbot (clone locally or open in Cursor).
- Access to **Ramion tailnet** and live app at `:8780`.
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
   | `RAMION_VIEWER_URL` | `http://ramion-server-01.tail0fbdb0.ts.net:8780/` |

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
   | `RAMION_BASE_URL` | `http://ramion-server-01.tail0fbdb0.ts.net:8780` |

## 4. Connect Tailscale for Monitor

Monitor must reach the private viewer from the agent runtime.

**Team tailnet (recommended for Ramion org):**

1. Cursor team admin enables Tailscale for Grok Bot (company tailnet).
2. Member authenticates device; admin applies posture limiting bot egress if required.
3. Confirm from agent shell or diagnostic: curl MagicDNS health URL (once server implements health) or viewer `/`.

**Personal tailnet alternative:** If the arm server is on a personal tailnet, use one-click Connect when you administer that tailnet; otherwise ask an admin to tag a `grokbot` device.

See Cursor Tailscale docs in product help — do not commit auth keys.

**Verify:**

```bash
curl -sS -o /dev/null -w "%{http_code}" http://ramion-server-01.tail0fbdb0.ts.net:8780/
```

Expect `200` (or `302` if redirect). Non-zero exit → fix Tailscale before demo.

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

## 6. Align API contract with real server

1. Open `api/contract.md`.
2. On `ramion-server-01`, list real routes (browser network tab + curl).
3. Update contract; remove *(proposed)* for implemented endpoints.
4. Adjust rubric thresholds in `bots/monitor/skills/grading-rubric/SKILL.md` if field names differ.

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
| Pass quiz | Tutor posts MagicDNS link |
| Exercise 1 | Learner opens gripper; Tutor pings Monitor |
| Monitor | PASS/FAIL visible in channel |

Use `demo/CHECKLIST.md` for judge timing.

## 10. Watcher (colleague — not configured here)

Document for ops only: Watcher runs on separate Grok Bot with its own repo; may use higher cadence video. Tutor/Monitor do not depend on Watcher for grading.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Monitor INCONCLUSIVE | Tailscale on agent; check `RAMION_BASE_URL` |
| Tutor shares URL early | Re-import quiz-gate skill; reinforce PERSONA |
| API 404 everywhere | Screenshot-only grading until server ships API |
| Learner off tailnet | Join tailnet before quiz pass |

## References

- Architecture: `docs/architecture.md`
- API: `api/contract.md`
- Demo: `demo/CHECKLIST.md`
