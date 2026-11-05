from __future__ import annotations

import unittest

from papaj_watcher.intent import (
    ACTION_REVIEW,
    ACTION_SOFT_STOP,
    ACTION_WARN,
    ALLOWED_ACTIONS,
    LEVEL_BAD_INTENT,
    LEVEL_NORMAL,
    LEVEL_SUSPICIOUS,
    PROFILE_BENIGN,
    PROFILE_DELIBERATE,
    PROFILE_NOVICE,
    IntentConfig,
    IntentEngine,
)
from papaj_watcher.rules import Finding

from support import load_state, mutate


def owned(state: dict, owner: str = "owner-fixture", label: str = "fixture-operator") -> dict:
    return mutate(state, control={"owner_id": owner, "label": label, "expires_in_s": 1.2})


def finding(rule: str, level: str, message: str = "") -> Finding:
    return Finding(level=level, rule=rule, message=message or rule, details={}, should_stop=(level == "critical"))


class IntentEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ok = owned(load_state("state_ok.json"))
        self.engine = IntentEngine(IntentConfig(window_s=60.0, cooldown_s=30.0))

    def test_benign_session_stays_normal_and_silent(self) -> None:
        event = self.engine.update(self.ok, [], [], 1.0, dry_run=True)
        assessment = self.engine.last_assessment
        self.assertIsNone(event)
        assert assessment is not None
        self.assertEqual(assessment.level, LEVEL_NORMAL)
        self.assertEqual(assessment.profile, PROFILE_BENIGN)
        self.assertEqual(assessment.score, 0)

    def test_novice_isolated_then_improving_is_not_bad_intent(self) -> None:
        engine = self.engine
        warning = finding("joint_near_limits", "warning", "near limit")
        engine.update(mutate(self.ok, measured={"shoulder_pan": 98.0}), [warning], [], 1.0, dry_run=True)
        engine.update(
            mutate(self.ok, clip="shoulder_pan clipped to 105.0"),
            [finding("velocity_spike", "warning", "brief spike")],
            [],
            2.0,
            dry_run=True,
        )
        engine.update(
            self.ok,
            [finding("rapid_command_bursts", "warning", "a few jogs")],
            [],
            3.0,
            dry_run=True,
        )
        # Time passes with clean motion — decreasing window, novice discount.
        event = engine.update(self.ok, [], [], 40.0, dry_run=True)
        assessment = engine.last_assessment
        assert assessment is not None
        self.assertEqual(assessment.profile, PROFILE_NOVICE)
        self.assertNotEqual(assessment.level, LEVEL_BAD_INTENT)
        self.assertEqual(assessment.recommended_action, ACTION_WARN)
        if event is not None:
            self.assertEqual(event["level"], LEVEL_SUSPICIOUS)
            self.assertEqual(event["recommended_action"], ACTION_WARN)
            self.assertEqual(event["profile"], PROFILE_NOVICE)

    def test_malicious_escalation_emits_bad_intent(self) -> None:
        engine = self.engine
        engine.update(self.ok, [finding("joint_near_limits", "warning", "near limit")], [], 1.0, dry_run=True)
        engine.update(
            mutate(self.ok, clip="shoulder_pan clipped to 105.0", target={"shoulder_pan": 200.0}),
            [finding("joint_near_limits", "critical", "pushed through the limit")],
            [],
            2.0,
            dry_run=True,
        )
        engine.update(self.ok, [finding("rapid_command_bursts", "critical", "burst")], [], 3.0, dry_run=True)
        engine.update(self.ok, [finding("collision_torque", "critical", "stall")], [], 4.0, dry_run=True)
        event = engine.update(
            self.ok,
            [finding("collision_torque", "critical", "stall again")],
            ["/tmp/sim-evidence.jpg"],
            5.0,
            dry_run=True,
        )
        self.assertIsNotNone(event)
        assert event is not None
        self.assertEqual(event["type"], "intent_alert")
        self.assertEqual(event["level"], LEVEL_BAD_INTENT)
        self.assertEqual(event["profile"], PROFILE_DELIBERATE)
        self.assertGreaterEqual(event["score"], 12.0)
        self.assertIn(event["recommended_action"], (ACTION_SOFT_STOP, ACTION_REVIEW))
        self.assertTrue(event["dry_run"])
        self.assertEqual(event["session"]["owner_id"], "owner-fixture")
        self.assertEqual(event["session"]["label"], "fixture-operator")
        codes = {item["code"] for item in event["reasons"]}
        self.assertIn("repeated_joint_near_limits_after_warning", codes)
        self.assertIn("collision_torque_repeats", codes)
        self.assertTrue(event["evidence"])
        slack = event["slack_text"]
        self.assertIn("text", slack)
        self.assertIn("blocks", slack)
        self.assertIn("intent", slack["text"].lower())
        self.assertTrue(isinstance(slack["blocks"], list) and slack["blocks"])

    def test_cooldown_suppresses_repeat_but_escalation_emits(self) -> None:
        engine = IntentEngine(IntentConfig(window_s=60.0, cooldown_s=30.0))
        engine.update(self.ok, [finding("joint_near_limits", "warning", "near")], [], 1.0, dry_run=True)
        first = engine.update(
            mutate(self.ok, clip="clipped"),
            [finding("joint_near_limits", "critical", "again")],
            [],
            2.0,
            dry_run=True,
        )
        self.assertIsNotNone(first)
        assert first is not None
        self.assertEqual(first["level"], LEVEL_SUSPICIOUS)
        repeat = engine.update(self.ok, [], [], 5.0, dry_run=True)
        self.assertIsNone(repeat)
        second = engine.update(
            self.ok,
            [
                finding("collision_torque", "critical", "stall"),
                finding("collision_torque", "critical", "stall 2"),
                finding("rapid_command_bursts", "critical", "more bursts"),
            ],
            [],
            6.0,
            dry_run=True,
        )
        self.assertIsNotNone(second)
        assert second is not None
        self.assertEqual(second["level"], LEVEL_BAD_INTENT)

    def test_motion_after_stop_and_reclaim(self) -> None:
        engine = self.engine
        engine.update(self.ok, [], [], 1.0, dry_run=True)
        vacated = mutate(
            self.ok,
            control={"owner_id": None, "label": None, "expires_in_s": 0.0},
            target={"shoulder_pan": 25.0},
            measured={"shoulder_pan": 0.0},
        )
        engine.update(vacated, [], [], 2.0, dry_run=True)
        moving = engine.evaluate(vacated, [], 3.0)
        # motion_after_stop is recorded on the unleased session
        self.assertTrue(any(reason["code"] == "motion_after_stop" for reason in moving.reasons))
        reclaim = engine.evaluate(self.ok, [], 4.0)
        self.assertTrue(any(reason["code"] == "reclaim_after_stop" for reason in reclaim.reasons))
        self.assertEqual(reclaim.profile, PROFILE_DELIBERATE)

    def test_stale_loop_abuse(self) -> None:
        engine = self.engine
        engine.update(self.ok, [], [], 1.0, dry_run=True)
        stale = mutate(self.ok, age_s=4.0, loop_ok=False, target={"shoulder_pan": 40.0})
        assessment = engine.evaluate(stale, [], 2.0)
        self.assertTrue(any(reason["code"] == "stale_loop_abuse" for reason in assessment.reasons))

    def test_vision_unsafe_can_recommend_human_review(self) -> None:
        engine = self.engine
        engine.update(self.ok, [finding("joint_near_limits", "warning", "near")], [], 1.0, dry_run=True)
        event = engine.update(
            mutate(self.ok, clip="clipped", target={"shoulder_pan": 180.0}),
            [
                finding("joint_near_limits", "critical", "again"),
                finding("vision_unsafe", "critical", "hand in workspace"),
                finding("rapid_command_bursts", "critical", "burst"),
            ],
            [],
            2.0,
            dry_run=True,
        )
        self.assertIsNotNone(event)
        assert event is not None
        self.assertEqual(event["level"], LEVEL_BAD_INTENT)
        self.assertEqual(event["recommended_action"], ACTION_REVIEW)

    def test_never_recommends_estop_or_automatic_revoke_token(self) -> None:
        engine = self.engine
        engine.update(self.ok, [finding("joint_near_limits", "warning", "near")], [], 1.0, dry_run=True)
        event = engine.update(
            mutate(self.ok, clip="clipped", target={"shoulder_pan": 180.0}),
            [
                finding("joint_near_limits", "critical", "again"),
                finding("collision_torque", "critical", "stall"),
                finding("collision_torque", "critical", "stall 2"),
                finding("rapid_command_bursts", "critical", "burst"),
            ],
            [],
            2.0,
            dry_run=True,
        )
        self.assertIsNotNone(event)
        assert event is not None
        self.assertIn(event["recommended_action"], ALLOWED_ACTIONS)
        self.assertNotIn(event["recommended_action"], {"e-stop", "estop", "revoke", "revoke_access"})
        blob = str(event)
        self.assertNotIn("emergency-stop", blob)

    def test_slack_text_is_plain_text_plus_block_kit(self) -> None:
        from papaj_watcher.intent import format_slack_text

        payload = format_slack_text(
            level=LEVEL_BAD_INTENT,
            score=18.0,
            session={"owner_id": "owner-fixture", "label": "fixture-operator"},
            profile=PROFILE_DELIBERATE,
            reasons=[{"code": "demo", "detail": "repeated joint_near_limits after warning", "weight": 3}],
            recommended_action=ACTION_REVIEW,
            dry_run=True,
        )
        self.assertIn("fixture-operator", payload["text"])
        self.assertIn("revoke_access_human_review", payload["text"])
        types = [block.get("type") for block in payload["blocks"]]
        self.assertIn("header", types)
        self.assertIn("section", types)
        self.assertIn("context", types)


if __name__ == "__main__":
    unittest.main()
