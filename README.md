# RAMION — Your first real robot move. Guided by Grok.

**Learn robotics by controlling a real arm — with an AI tutor beside you.**

Getting started takes more than access to hardware. Beginners need guidance; remote lab operators need visibility. RAMION brings both to the same robot session.

![RAMION: a learner guided by TUTOR operates a real robot while WATCHER observes the session](docs/ramion-solution.png)
<sub>Concept overview. TUTOR runs in Grok Bot; WATCHER is a separate monitoring service. Automatic software stop is optional and off by default.</sub>

## From curious to in control

1. **Learn.** TUTOR explains the basics, checks your understanding with three questions, and gives you the app link.
2. **Move.** Open the gripper. Close it. Rotate the arm's base by 90°.
3. **Get feedback.** Say “done.” TUTOR compares screenshots from before and after your attempt, using robot readings to check the rotation.

**For the operator:** WATCHER checks camera views and robot readings, flagging concerning activity in Slack for human review.

**The idea:** Grok Bot becomes a coach that can see the result of your actions in the physical world.

---

**[Get robot access →](https://ramion.cloud/)** · [TUTOR & template setup](tutor/) · [WATCHER](packages/watcher/)

<sub>Wrocław Grok Bot Hackathon · November 5, 2026 · Prototype: Grok Bot tutor recipe + runnable monitoring service. [Demo checks](tutor/DEMO_CHECKS.md).</sub>
