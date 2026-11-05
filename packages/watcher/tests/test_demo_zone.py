"""Demo forbidden zone: shoulder_pan < -60 (soft demo limit, hardware limit is -105)."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from papaj_watcher.config import Thresholds, load_thresholds
from papaj_watcher.intent import (
    ACTION_REVIEW,
    ACTION_WARN,
    LEVEL_BAD_INTENT,
    LEVEL_SUSPICIOUS,
    IntentConfig,
    IntentEngine,
)
from papaj_watcher.rules import RuleEngine

from support import load_state, mutate

DEMO_JSON = Path(__file__).resolve().parents[1] / "demo" / "thresholds.demo.json"


def pan(value: float) -> dict:
    return mutate(load_state(), measured={"shoulder_pan": value}, command={"shoulder_pan": value},
                  target={"shoulder_pan": value})


class DemoZoneTest(unittest.TestCase):
    def setUp(self):
        self.thresholds = load_thresholds(DEMO_JSON, None)
        self.rules = RuleEngine(self.thresholds)
        self.intent = IntentEngine(IntentConfig(demo_zones=self.thresholds.demo_zones))

    def step(self, value: float, now: float):
        state = pan(value)
        findings = self.rules.evaluate(state, now)
        return findings, self.intent.update(state, findings, [], now, dry_run=True)

    def test_demo_file_contents(self):
        data = json.loads(DEMO_JSON.read_text())
        self.assertEqual(data, {"demo_zones": [{"joint": "shoulder_pan", "below": -60, "name": "demo_left_zone"}]})
        self.assertEqual(self.thresholds.demo_zones[0]["below"], -60.0)

    def test_outside_zone_is_quiet(self):
        findings, event = self.step(-30.0, 0.0)
        self.assertFalse([f for f in findings if f.rule == "forbidden_zone"])
        self.assertIsNone(event)

    def test_finding_message_and_never_stops(self):
        findings, _ = self.step(-72.3, 0.0)
        zone = [f for f in findings if f.rule == "forbidden_zone"]
        self.assertEqual(len(zone), 1)
        self.assertEqual(zone[0].message, "shoulder_pan -72.3° is below demo limit -60°")
        self.assertFalse(zone[0].should_stop)

    def test_single_entry_is_suspicious_warn_demo(self):
        _, event = self.step(-65.0, 0.0)
        self.assertEqual(event["level"], LEVEL_SUSPICIOUS)
        self.assertEqual(event["recommended_action"], ACTION_WARN)
        self.assertTrue(event["demo"])
        self.assertTrue(event["slack_text"]["text"].startswith("[DEMO]"))

    def test_dwell_three_seconds_escalates(self):
        self.step(-65.0, 0.0)
        _, mid = self.step(-66.0, 1.5)
        self.assertIsNone(mid)
        _, event = self.step(-67.0, 3.1)
        self.assertEqual(event["level"], LEVEL_BAD_INTENT)
        self.assertEqual(event["recommended_action"], ACTION_REVIEW)
        self.assertIn("forbidden_zone_dwell", [r["code"] for r in event["reasons"]])

    def test_reentry_escalates_then_no_spam(self):
        events = [self.step(v, t)[1] for t, v in enumerate([-30, -65, -70, -40, -68])]
        emitted = [e for e in events if e]
        self.assertEqual([e["level"] for e in emitted], [LEVEL_SUSPICIOUS, LEVEL_BAD_INTENT])
        self.assertEqual(emitted[-1]["recommended_action"], ACTION_REVIEW)
        more = [self.step(v, 5 + i)[1] for i, v in enumerate([-30, -70, -30, -75])]
        self.assertEqual([e for e in more if e], [])

    def test_no_zones_by_default(self):
        self.assertEqual(Thresholds().demo_zones, [])
        rules = RuleEngine(Thresholds())
        self.assertFalse([f for f in rules.evaluate(pan(-80.0), 0.0) if f.rule == "forbidden_zone"])

    def test_bad_zone_config_rejected(self):
        with self.assertRaises(ValueError):
            Thresholds().overlay({"demo_zones": [{"joint": "shoulder_pan"}]})


if __name__ == "__main__":
    unittest.main()
