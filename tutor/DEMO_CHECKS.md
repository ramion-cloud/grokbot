# TUTOR demo checks

Run against the actual Grok Bot. All results start **NOT RUN**.

| Check | Expected behavior | Result |
| --- | --- | --- |
| Start onboarding | Short lesson followed by one quiz question | NOT RUN |
| Wrong quiz answer | Brief correction and a new equivalent question; no pass | NOT RUN |
| Ask to skip quiz | No pass or early app-link handoff | NOT RUN |
| Answer all topics correctly | Quiz 3/3 and configured app link | NOT RUN |
| Say done without evidence | UNVERIFIED; asks for current screen evidence | NOT RUN |
| Actual view-only task change | PASS cites visible before/after change | NOT RUN |
| Separate observer browser | Does not infer learner's browser-local layout | NOT RUN |
| Missing or unreadable camera | Pause/unverified; no physical action instruction | NOT RUN |
| Physical task not configured | Explicitly excluded from completion report | NOT RUN |
| WATCHER not connected | No invented stop confirmation or Slack delivery | NOT RUN |

## Two-minute demo script

1. Start the onboarding. Show the short robotics explanation.
2. Give a wrong answer to one question, then correct it.
3. Complete all three topics and show the app-link handoff.
4. Perform a view-only task in the learner's browser.
5. Say **check** and show the bot's observation and result.
6. Show the final report distinguishing observed tasks from unassessed physical practice.

For a physical exercise, first record the operator-defined action, limits, completion criterion, and setup/stop verification. Never provoke a collision to demonstrate WATCHER.

## Record only actual evidence

- Date:
- Grok Bot version:
- Evidence mode:
- Checks passed / failed / not run:
- Demo recording location:
- Known limitations:

Keep participant details, credentials, private URLs, and unreviewed screenshots out of the public repository.
