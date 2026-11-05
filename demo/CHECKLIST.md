# Judge demo checklist (~3 minutes)

Use this path live in the **group channel** with Tutor + Monitor connected to Tailscale and `:8780` reachable.

## Before you start (presenter, off-camera)

- [ ] Tailscale up on learner laptop and Monitor agent environment.
- [ ] `RAMION_BASE_URL` / viewer loads: http://ramion-server-01.tail0fbdb0.ts.net:8780/
- [ ] Group channel includes learner, Tutor, Monitor.
- [ ] Optional: Discord ops webhook tested.
- [ ] README architecture diagram ready to show (screen share tab).

## Minute 0:00 — Framing (presenter)

- [ ] State repo was **empty**; this is the **agent-native recipe** for Ramion (not the robot server binary).
- [ ] Name agents: Tutor teaches + gates; Monitor grades; Watcher **out of scope**; hard e-stop on robot.
- [ ] Show mermaid diagram in `README.md` or `docs/architecture.md`.

## Minute 0:30 — Tutor intro + quiz

- [ ] Learner: “I’m new — start the lab.”
- [ ] Tutor delivers short curriculum (curriculum-intro skill).
- [ ] Tutor runs 3-question quiz (quiz-gate skill).
- [ ] **Fail demo optional (10s):** wrong answer → no link → correct → pass.

## Minute 1:30 — Viewer access

- [ ] Tutor posts MagicDNS viewer URL only after 3/3 pass.
- [ ] Learner confirms page loads (share viewer tab briefly).

## Minute 2:00 — Graded exercise

- [ ] Tutor assigns **Exercise 1: open-gripper** (exercise-script skill).
- [ ] Learner operates gripper **Open** in UI; says “done”.
- [ ] Tutor invokes Monitor: `grade exercise-id=open-gripper timeout_sec=60`.
- [ ] Monitor runs observe-session (screenshots + optional API).

## Minute 2:30 — Result

- [ ] Monitor posts `[open-gripper] RESULT: PASS` (or FAIL with clear reason).
- [ ] Tutor acknowledges; if PASS, tease Exercise 2 or completion message.

## Minute 2:45 — Safety boundary (presenter)

- [ ] One sentence: soft-stop via API + Discord; hardware e-stop not in chat.
- [ ] Watcher handled by colleague agent — not shown today.

## Stretch (if time)

- [ ] Exercise 2 close-gripper PASS.
- [ ] Tutor mentions Template share for other hackathon teams.

## Abort criteria

| Issue | Fallback narrative |
|-------|---------------------|
| Arm offline | Show Monitor INCONCLUSIVE message + screenshot rubric in skills |
| Network down | Walk through `docs/architecture.md` data flow |
| API not built | Emphasize proposed contract in `api/contract.md` |

## Artifacts to point judges to

| File | Purpose |
|------|---------|
| `README.md` | Pitch + diagram |
| `docs/architecture.md` | Boundaries + screenshot vs RTSP |
| `api/contract.md` | Honest proposed HTTP surface |
| `bots/tutor/skills/` | Executable teaching logic |
| `bots/monitor/skills/` | Grading + observation |
| `SETUP.md` | Repro steps |

## Success definition for judging

- [ ] Multi-agent **coordination** visible in channel (Tutor ≠ grader).
- [ ] Tailscale **private** reachability explained.
- [ ] Grok Bot used as **operational agents**, not a one-shot code generator.
- [ ] Safety model honest (soft vs hard stop, Watcher boundary).
