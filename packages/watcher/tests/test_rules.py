from __future__ import annotations

import unittest

from papaj_watcher.config import Thresholds
from papaj_watcher.rules import RuleEngine

from support import load_state, mutate


def engine() -> RuleEngine:
    return RuleEngine(Thresholds(emit_cooldown_s=0.0))


class RuleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ok = load_state("state_ok.json")

    def test_healthy_fixture_is_quiet(self) -> None:
        findings = engine().evaluate(self.ok, 1.0)
        self.assertEqual(findings, [])

    def test_joint_near_limit_warning_and_critical(self) -> None:
        warning_state = mutate(
            self.ok,
            measured={"shoulder_pan": 98.0},
            command={"shoulder_pan": 98.0},
            target={"shoulder_pan": 98.0},
        )
        warning = engine().evaluate(warning_state, 1.0)
        self.assertTrue(any(item.rule == "joint_near_limits" and item.level == "warning" for item in warning))
        self.assertFalse(any(item.should_stop for item in warning))

        critical_state = load_state("state_near_limit.json")
        critical = engine().evaluate(critical_state, 1.0)
        hits = [item for item in critical if item.rule == "joint_near_limits" and item.level == "critical"]
        self.assertTrue(hits)
        self.assertTrue(hits[0].should_stop)

    def test_velocity_spike_from_successive_samples(self) -> None:
        rules = engine()
        rules.evaluate(self.ok, 0.0)
        fast = mutate(self.ok, measured={"shoulder_pan": 80.0})
        findings = rules.evaluate(fast, 0.25)  # 320 deg/s vs 140 cap
        hits = [item for item in findings if item.rule == "velocity_spike" and item.level == "critical"]
        self.assertTrue(hits)
        self.assertEqual(hits[0].details["joint"], "shoulder_pan")

    def test_temperature_and_current_when_present(self) -> None:
        state = mutate(
            self.ok,
            temperatures={"elbow_flex": 81.0},
            currents={"elbow_flex": 900.0},
        )
        findings = engine().evaluate(state, 1.0)
        self.assertTrue(any(item.rule == "temperature_spike" and item.level == "critical" for item in findings))
        self.assertTrue(any(item.rule == "current_spike" and item.level == "warning" for item in findings))

    def test_nested_telemetry_maps_are_read(self) -> None:
        state = mutate(self.ok, telemetry={"present_temperature": {"wrist_flex": 61.0}})
        findings = engine().evaluate(state, 1.0)
        self.assertTrue(any(item.rule == "temperature_spike" and item.level == "warning" for item in findings))

    def test_collision_tracking_error(self) -> None:
        state = mutate(self.ok, command={"shoulder_lift": 50.0}, measured={"shoulder_lift": -20.0})
        findings = engine().evaluate(state, 1.0)
        hits = [item for item in findings if item.rule == "collision_torque" and item.level == "critical"]
        self.assertTrue(hits)

    def test_polish_and_english_fault_strings(self) -> None:
        polish = mutate(self.ok, faults=["shoulder_lift (serwo 2): przeciazenie"])
        english = mutate(self.ok, faults=["shoulder_pan: overload, overheating"])
        self.assertTrue(any(item.should_stop for item in engine().evaluate(polish, 1.0)))
        self.assertTrue(any(item.should_stop for item in engine().evaluate(english, 1.0)))

    def test_rapid_command_bursts(self) -> None:
        rules = engine()
        rules.evaluate(self.ok, 0.0)
        last = []
        for index in range(1, 10):
            state = mutate(self.ok, target={"gripper": float(index)})
            last = rules.evaluate(state, index * 0.08)
        self.assertTrue(any(item.rule == "rapid_command_bursts" for item in last))

    def test_motion_without_lease_is_critical(self) -> None:
        state = mutate(
            self.ok,
            control={"owner_id": None, "label": None, "expires_in_s": 0.0},
            target={"shoulder_pan": 25.0},
        )
        findings = engine().evaluate(state, 1.0)
        hits = [item for item in findings if item.rule == "lease_anomaly" and item.should_stop]
        self.assertTrue(hits)

    def test_lease_expiry_while_moving(self) -> None:
        state = mutate(
            self.ok,
            control={"owner_id": "owner-fixture", "label": "fixture-operator", "expires_in_s": 0.1},
            target={"shoulder_pan": 20.0},
        )
        findings = engine().evaluate(state, 1.0)
        self.assertTrue(any(item.rule == "lease_anomaly" and item.level == "warning" for item in findings))

    def test_owner_flicker(self) -> None:
        rules = engine()
        rules.evaluate(self.ok, 0.0)
        findings = []
        for index, owner in enumerate(("a", "b", "c"), start=1):
            state = mutate(self.ok, control={"owner_id": owner, "label": "fixture-operator", "expires_in_s": 1.2})
            findings = rules.evaluate(state, float(index))
        self.assertTrue(any("owner changed" in item.message for item in findings))

    def test_stale_and_disconnected(self) -> None:
        stale = engine().evaluate(mutate(self.ok, age_s=3.5), 1.0)
        self.assertTrue(any(item.rule == "lease_anomaly" and item.level == "critical" for item in stale))
        disconnected = engine().evaluate(mutate(self.ok, connected=False), 1.0)
        self.assertTrue(any("disconnected" in item.message for item in disconnected))

    def test_latched_estop_suppresses_stop_request(self) -> None:
        state = mutate(
            self.ok,
            measured={"shoulder_pan": 104.0},
            emergency_stop={"latched": True, "generation": 3, "hold_status": "held", "hold_error": None},
        )
        findings = engine().evaluate(state, 1.0)
        self.assertTrue(any(item.rule == "joint_near_limits" for item in findings))
        self.assertFalse(any(item.should_stop for item in findings))

    def test_emit_cooldown_suppresses_repeats(self) -> None:
        rules = RuleEngine(Thresholds(emit_cooldown_s=2.0))
        state = mutate(self.ok, measured={"shoulder_pan": 104.0})
        first = rules.evaluate(state, 1.0)
        second = rules.evaluate(state, 2.0)
        third = rules.evaluate(state, 3.5)
        self.assertTrue(first)
        self.assertEqual(second, [])
        self.assertTrue(third)


if __name__ == "__main__":
    unittest.main()
