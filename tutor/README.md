# RAMION TUTOR

A learner opens the bot and starts learning: short robotics intro, three-question quiz, app link, guided tasks, and feedback from visible progress.

The app address is built into [TUTOR_PROMPT.md](TUTOR_PROMPT.md). Learners do not supply configuration. The bot handles observation automatically and requests a screenshot only when it cannot inspect the learner's screen.

## Prepare the bot (creator only)

1. Create a new Grok Bot named **RAMION TUTOR**.
2. Paste the complete [TUTOR_PROMPT.md](TUTOR_PROMPT.md) into its chat. It starts the lesson immediately.
3. Run the [demo checks](DEMO_CHECKS.md). If updating an existing bot, this prompt explicitly replaces its previous instructions.
4. Before physical practice, the session host checks the robot, stop procedure, and available beginner exercise.

## Publish a Grok Bot template

1. Click the bot's name at the top of its chat.
2. Select **Share → Create a copy**.
3. Review the generated template. Ensure it includes the full learner instructions and fixed app link, starts fresh for each learner, and does not carry your test learner's progress.
4. Select **Publish** on the template card, then **Copy link**.
5. Add the resulting link to this README and your submission. Test an imported copy by sending **Hi**: it should start teaching without setup questions.

If **Create a copy** is unavailable, template sharing may be restricted by your team. On mobile, the documented action is **Share as Template**. After changing the source bot, use **Share → Update template** to update the published template.

A template gives recipients a copy of the bot; it does not transfer the creator's computer, sign-ins, or network access. Learners without app access should visit [ramion.cloud](https://ramion.cloud/) to get access and set up their Tailscale connection. If connection problems persist, they can contact the session host. The fixed lab address is part of this project-specific recipe; it does not make the app publicly reachable.

[Official Grok Bot template documentation](https://docs.x.ai/grok-bot/bots#share-a-bot), checked 2026-11-05.

## GitHub and template

GitHub holds the versioned source and checks. The Grok Bot template is the installable learner experience. Publishing one does not automatically publish or update the other.

**Template URL:** Not yet recorded here.
**Live validation:** Not run during preparation; record actual results in the checklist.

The quiz controls the lesson flow, not server permissions. Grade only visible results, and distinguish observation onboarding from physical practice.
