# Judge demo checklist (~3 minutes)

Use this path live in the **group channel** with Tutor + Monitor able to reach the dashboard (`RAMION_BASE_URL`).

## Before you start (presenter, off-camera)

- [ ] Learner and Monitor agent can reach the dashboard.
- [ ] `RAMION_BASE_URL` / `RAMION_VIEWER_URL` load the viewer (set privately; do not paste secrets into the repo).
- [ ] Group channel includes learner, Tutor, Monitor.
- [ ] Optional: Papaj Watcher running in dry-run with `PAPAJ_WEBHOOK_URL` or a JSONL log Monitor can read.
- [ ] Optional: ops webhook tested.
- [ ] README architecture diagram ready to show (screen share tab).

## Minute 0:00 — Framing (presenter)

- [ ] This repo is the **agent-native recipe** for Ramion (not the robot server binary).
- [ ] Name agents: Tutor teaches + gates; Monitor grades; Watcher (`packages/watcher`) emits safety alerts; hard e-stop on robot.
- [ ] Show mermaid diagram in `README.md` or `docs/architecture.md`.

## Minute 0:30 — Tutor intro + quiz

- [ ] Learner: “I’m new — start the lab.”
- [ ] Tutor delivers short curriculum (curriculum-intro skill).
- [ ] Tutor runs 3-question quiz (quiz-gate skill).
- [ ] **Fail demo optional (10s):** wrong answer → no link → correct → pass.

## Minute 1:30 — Viewer access

- [ ] Tutor posts `RAMION_VIEWER_URL` only after 3/3 pass.
- [ ] Learner confirms page loads (share viewer tab briefly).

## Minute 2:00 — Graded exercise

- [ ] Tutor assigns **Exercise 1: open-gripper** (exercise-script skill).
- [ ] Learner operates gripper **Open** in UI; says “done”.
- [ ] Tutor invokes Monitor: `grade exercise-id=open-gripper timeout_sec=60`.
- [ ] Monitor runs observe-session (screenshots + `GET /api/state`).

## Minute 2:30 — Result

- [ ] Monitor posts `[open-gripper] RESULT: PASS` (or FAIL with clear reason).
- [ ] Tutor acknowledges; if PASS, tease Exercise 2 or completion message.

## Minute 2:45 — Safety boundary (presenter)

- [ ] One sentence: software soft-stop is `POST /api/stop`; hardware e-stop is not in chat.
- [ ] Watcher lives in `packages/watcher`; Monitor reads its webhook/JSONL alerts (`level`, `rule`) and does not re-run those heuristics. Dry-run is the default.

## Stretch (if time)

- [ ] Exercise 2 close-gripper PASS.
- [ ] Tutor mentions Template share for other hackathon teams.

## Abort criteria

| Issue | Fallback narrative |
|-------|---------------------|
| Arm offline | Show Monitor INCONCLUSIVE message + screenshot rubric in skills |
| Network down | Walk through `docs/architecture.md` data flow |
| `GET /api/state` unreachable | Screenshot-only grading; show verified contract in `api/contract.md` |

## Artifacts to point judges to

| File | Purpose |
|------|---------|
| `README.md` | Pitch + diagram |
| `docs/architecture.md` | Boundaries + screenshot vs RTSP + Watcher alerts |
| `api/contract.md` | Verified HTTP surface + Watcher alert JSON |
| `packages/watcher/` | Safety observer (dry-run by default) |
| `bots/tutor/skills/` | Executable teaching logic |
| `bots/monitor/skills/` | Grading + observation |
| `SETUP.md` | Repro steps |

## Success definition for judging

- [ ] Multi-agent **coordination** visible in channel (Tutor ≠ grader).
- [ ] Private **reachability** explained without pasting secrets.
- [ ] Grok Bot used as **operational agents**, not a one-shot code generator.
- [ ] Safety model honest (soft vs hard stop; Watcher alerts vs Monitor grades).
