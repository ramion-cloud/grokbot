# TUTOR demo checks

Run against the actual Grok Bot and an imported template copy. All results start **NOT RUN**.

| Check | Expected behavior | Result |
| --- | --- | --- |
| New learner says Hi | Intro and first quiz question immediately; no setup questions | NOT RUN |
| Wrong quiz answer | Short correction and follow-up on the missed concept | NOT RUN |
| Ask to skip quiz | Continues teaching; no early app-link handoff | NOT RUN |
| Three topics answered correctly | Clickable http://ramion-server-01:8780/ link | NOT RUN |
| Learner opens the app | First observation task; no URL or mode request | NOT RUN |
| Bot cannot see learner screen | Plain request for a screenshot | NOT RUN |
| Say done without visible evidence | Explains what view is needed; does not invent completion | NOT RUN |
| Actual task change | Feedback names the visible result | NOT RUN |
| Separate browser | Does not infer the learner's browser-local layout | NOT RUN |
| Private app is unreachable | Directs learner to host for connectivity help | NOT RUN |
| Physical exercise readiness unknown | Completes observation lesson honestly; host handles first movement | NOT RUN |
| Imported template, fresh learner | Retains lesson and address; no inherited quiz pass or task progress | NOT RUN |

## Two-minute demo

1. Say **Hi** and show the short lesson.
2. Answer one question incorrectly, then correct it.
3. Finish the quiz and open the supplied app link.
4. Complete a visible observation task.
5. Say **check** and show the tutor's specific feedback.
6. Show the recap of tasks actually completed.

Physical practice requires a host-prepared session and exercise. Do not provoke a collision for the demo.

## Record results

- Date:
- Grok Bot version:
- Template URL:
- Checks passed / failed / not run:
- Demo recording:
- Known limitations:

Do not publish credentials, participant details, or unreviewed camera images.
