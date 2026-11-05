---
name: ramion-curriculum-intro
description: >-
  Deliver Ramion's short robotics intro before quiz and viewer access.
  Use at session start or when learner asks for background.
---

# Curriculum intro (≈2 minutes)

Deliver this content in chat, broken into 3–4 messages. Pause for “ready” before quiz.

## 1. What Ramion is

Ramion lets software developers **rent time** on a real robotic arm and **operate it remotely** through a browser viewer. You learn by doing — with safety gates and an automated grader (Monitor).

## 2. What you’re controlling

- **Manipulator:** serial arm with multiple joints (exact count depends on cell — often 6 DOF + gripper).
- **Gripper:** end effector open/close — your first exercises use this.
- **Viewer:** the UI at the Tailscale URL; your commands go to the Ramion server, then the robot stack.

## 3. Safety (non-negotiable)

1. **Hardware e-stop** on the cell beats everything — bots cannot replace it.
2. **Soft-stop** in software freezes motion; Tutor can trigger via API; you can ask for “stop” anytime.
3. Stay within assigned exercises until Tutor advances you.
4. A separate **Watcher** agent (not in this chat) may flag abuse — cooperate if ops contacts you.

## 4. How this chat works

- **Tutor (me):** intro, quiz, link, exercises.
- **Monitor:** watches viewer/API and returns PASS/FAIL — I don’t grade motion myself.
- You operate the arm in the viewer; I never skip Monitor for scored steps.

## Check understanding (optional)

Ask: “In one sentence, who grades your gripper exercise?”  
Expected: Monitor (not Tutor).

When learner confirms ready → invoke **quiz-gate** skill.
