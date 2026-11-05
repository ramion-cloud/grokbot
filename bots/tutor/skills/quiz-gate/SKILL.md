---
name: ramion-quiz-gate
description: >-
  Three-question safety and flow quiz. Learner must pass before Tutor shares viewer URL.
---

# Quiz gate

**Passing score:** 3/3 correct. No partial pass for link sharing.

Ask one question at a time; wait for answer. Do not reveal all answers upfront.

## Q1 — Emergency stop

**Question:** If the arm moves unexpectedly, what should you use first **on the hardware**?

| Answer | Verdict |
|--------|---------|
| Physical e-stop on the robot/cell | ✅ Correct |
| Close the browser tab | ❌ Retry |
| Ask Tutor to “undo” | ❌ Retry |
| Only soft-stop API | ❌ Retry — soft-stop is software; hardware e-stop is primary |

## Q2 — Who grades exercises?

**Question:** After you open or close the gripper in the viewer, who decides PASS/FAIL?

| Answer | Verdict |
|--------|---------|
| Monitor bot | ✅ Correct |
| Tutor (this chat) | ❌ Retry |
| Watcher bot | ❌ Retry — Watcher is for abuse/safety monitoring, not lesson grading |
| Automatic email | ❌ Retry |

## Q3 — Network access

**Question:** Why do we share the MagicDNS link (`ramion-server-01.tail0fbdb0.ts.net`) instead of a public URL?

| Answer | Verdict |
|--------|---------|
| Viewer is on private Tailscale tailnet | ✅ Correct (accept variations mentioning VPN/tailnet/private) |
| GitHub requires it | ❌ Retry |
| Faster DNS | ❌ Retry |
| Monitor cannot use HTTPS | ❌ Retry |

## On pass

Reply:

```text
Quiz passed ✅
Viewer (Tailscale): http://ramion-server-01.tail0fbdb0.ts.net:8780/
Alternate on tailnet: http://ramion-server-01:8780/
Confirm you can load the page, then say "ready for exercise 1".
```

## On fail

Explain missed concept in one sentence; re-ask only failed questions.

**Do not** share viewer URL until 3/3 correct.
