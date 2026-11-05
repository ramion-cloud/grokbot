---
name: ramion-exercise-script
description: >-
  Hands-on exercise briefs for the live viewer. Tutor assigns; Monitor grades per rubric.
---

# Exercise scripts

Assign in order for first-time learners. After each assignment, message Monitor with:

```text
@monitor grade exercise-id=<id> timeout_sec=60
```

Replace `@monitor` with your channel’s invocation pattern (see SETUP.md).

---

## Exercise 1 — `open-gripper`

**Goal:** Fully open the gripper using the viewer controls.

**Tutor script:**

```text
Exercise 1: Open gripper
1. Open the viewer if not already.
2. Find the gripper control (Open / slider).
3. Command OPEN and hold until motion completes.
4. Reply "done" when finished.
```

**Pass hint (after FAIL only):** Ensure you clicked Open, not Close; wait until motion idle.

**Monitor:** rubric `open-gripper`.

---

## Exercise 2 — `close-gripper`

**Goal:** Fully close the gripper from an open state.

**Tutor script:**

```text
Exercise 2: Close gripper
1. Start from open if possible.
2. Command CLOSE in the viewer.
3. Reply "done" when fingers meet / closed state shown.
```

**Pass hint:** If already closed, open first (Exercise 1), then close.

**Monitor:** rubric `close-gripper`.

---

## Exercise 3 — `move-home`

**Goal:** Move arm to home/ready preset via viewer (button or menu).

**Tutor script:**

```text
Exercise 3: Move to home
1. Locate "Home" or "Ready" preset in the viewer.
2. Execute preset; keep clear of virtual obstacles.
3. Reply "done" when arm stops moving.
```

**Pass hint:** Wait for motion to finish before saying done.

**Monitor:** rubric `move-home`.

**TODO (team):** Align preset name with real UI label on `:8780`.

---

## Completion

When Monitor returns PASS for all three:

```text
All core exercises passed 🎉
You’ve completed the Ramion Grok Bot lab loop: quiz → viewer → graded motion.
Next: explore Ramion rentals / advanced paths with your team.
```

## Soft-stop drill (optional, not graded by default)

If ops requests demo of soft-stop only:

- Tutor calls proposed `POST /api/v1/control/soft-stop`.
- Explain hardware e-stop is separate.
- Do not count as Watcher demo.
