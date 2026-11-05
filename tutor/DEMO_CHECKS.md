# TUTOR demo checks

Run against the real Grok Bot and an imported template copy. All results are **NOT RUN** until observed.

| Check | Expected behavior | Result |
| --- | --- | --- |
| Learner says Hi | Starts lesson; opens app in background without setup questions | NOT RUN |
| Quiz wrong answer | Explains and checks the missed concept | NOT RUN |
| Quiz pass | Supplies fixed robot app link | NOT RUN |
| Observation session | Confirms same robot/session and current feed | NOT RUN |
| Before task | Captures baseline before giving movement instruction | NOT RUN |
| Learner says done | Captures a new screenshot automatically | NOT RUN |
| Open gripper | Compares finger separation before/after; verifies open state | NOT RUN |
| Already open baseline | Starts with close exercise; no unchanged-state pass | NOT RUN |
| Close empty gripper | Confirms visible closing and normal closed state | NOT RUN |
| Rotate from -20 degrees by +90 | Target is +70, not +90; grades measured result within 5 degrees | NOT RUN |
| Target changes but robot does not | Does not pass based on target alone | NOT RUN |
| No measured angles | Does not estimate exact 90 degrees from camera perspective | NOT RUN |
| 90-degree move exceeds allowed range | Does not assign that direction or bypass limits | NOT RUN |
| Missing, stale, or wrong-session evidence | Does not pass; resolves observation problem | NOT RUN |
| Learner lacks access | Links ramion.cloud and explains Tailscale requirement | NOT RUN |
| Bot cannot reach app | Explains observation failure; offers disclosed image fallback | NOT RUN |
| Imported template | Has lesson and fixed URL, no inherited quiz/task passes | NOT RUN |

## Demo

1. Say Hi; complete the quiz.
2. Show TUTOR capturing the baseline before the open-gripper instruction.
3. Operate the gripper; say done; show the new screenshot and comparison.
4. Repeat with closing the empty gripper.
5. In a host-prepared session, demonstrate the 90-degree base rotation with measured start and end angles.
6. Show the recap, including any unverified or skipped exercise.

## Record actual results

- Date and Grok Bot version:
- Template URL:
- Checks passed / failed / not run:
- Evidence references:
- Known limitations:

Keep credentials, participant details, and unreviewed camera images out of the public repository.
