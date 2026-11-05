# RAMION TUTOR

A learner opens the bot and starts learning: robotics intro, three-question quiz, app link, then physical exercises assessed from before/after evidence.

## Learner flow

1. TUTOR opens the robot app in its own background browser while teaching.
2. The learner passes the quiz and opens the supplied app link.
3. Before each exercise, TUTOR captures a baseline screenshot.
4. The learner performs the task and says **done**.
5. TUTOR takes a fresh screenshot, compares the result, and gives feedback.

Core exercises: **open the gripper**, **close the empty gripper**, and **rotate the base joint by 90 degrees**. Rotation is a change from the measured starting angle, with a stated grading tolerance of 5 degrees. Exact rotation needs measured angles, not a visual estimate. Use only permitted movements in a host-prepared workspace.

The bot observes; the learner operates. No continuous polling or manual image upload is required in the normal flow. Uploaded before/after screenshots are a disclosed fallback if the bot cannot access the app.

## Prepare and publish (creator only)

1. Create **RAMION TUTOR** and paste the complete [TUTOR_PROMPT.md](TUTOR_PROMPT.md). It replaces the previous recipe and immediately starts teaching.
2. Confirm the bot's background browser can reach the correct robot and see current camera frames. Learner connectivity alone is insufficient.
3. Run [DEMO_CHECKS.md](DEMO_CHECKS.md).
4. Click the bot name → **Share → Create a copy**.
5. Review that the template includes all instructions and the fixed app link, without test learner progress.
6. Select **Publish → Copy link** and add the link to the submission. Test a fresh imported copy.
7. After changes, use **Share → Update template**.

[Official template documentation](https://docs.x.ai/grok-bot/bots), checked 2026-11-05. Team policy can restrict sharing. On mobile the documented action is **Share as Template**.

Templates copy the bot instructions, not the creator's computer, sign-ins, or network access. Learners without access should visit [ramion.cloud](https://ramion.cloud/) to get access and set up Tailscale. The host must also arrange connectivity for the bot's observation browser.

## Status

GitHub stores the recipe; it does not automatically update a published Grok Bot template.
**Template URL:** Not yet recorded here.
**Live validation:** Not run during preparation. Screenshot capture, session matching, and measured-angle grading must be checked in the actual app.

The quiz controls the lesson flow, not server permissions. Physical exercises require normal robot limits and a host-checked workspace; screenshot assessment does not establish trajectory safety.
