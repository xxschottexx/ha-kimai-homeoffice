"""Tests for option defaults and MQTT payload parsing."""

import ast
import json
from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).parents[1]


def _constant_values() -> dict[str, object]:
    """Load literal constants without importing Home Assistant."""
    tree = ast.parse(
        (ROOT / "custom_components/kimai_homeoffice/const.py").read_text(
            encoding="utf-8"
        )
    )
    values: dict[str, object] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if isinstance(target, ast.Name) and target.id.startswith("DEFAULT_"):
            values[target.id] = ast.literal_eval(node.value)
    return values


def _mqtt_parser():
    """Load the pure MQTT payload parser without importing Home Assistant."""
    path = ROOT / "custom_components/kimai_homeoffice/__init__.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "_parse_mqtt_button_payload"
    )
    namespace = {"json": json}
    exec(compile(ast.Module([function], []), path, "exec"), namespace)
    return namespace["_parse_mqtt_button_payload"]


class OptionsDefaultsTest(TestCase):
    """Test goal and button option defaults."""

    def test_goal_defaults(self) -> None:
        """Missing goal options retain the documented defaults."""
        defaults = _constant_values()

        self.assertTrue(defaults["DEFAULT_DAILY_GOAL_ENABLED"])
        self.assertEqual(defaults["DEFAULT_DAILY_GOAL_HOURS"], 7)
        self.assertEqual(defaults["DEFAULT_DAILY_GOAL_MINUTES"], 0)
        self.assertTrue(defaults["DEFAULT_WEEKLY_GOAL_ENABLED"])
        self.assertEqual(defaults["DEFAULT_WEEKLY_GOAL_HOURS"], 35)
        self.assertEqual(defaults["DEFAULT_WEEKLY_GOAL_MINUTES"], 0)
        self.assertFalse(defaults["DEFAULT_BUTTON_ENABLED"])


class MqttPayloadTest(TestCase):
    """Test MQTT button payload parsing."""

    def test_plain_payload(self) -> None:
        """Plain text and byte payloads are accepted without a JSON key."""
        parser = _mqtt_parser()

        self.assertEqual(parser("single", None), "single")
        self.assertEqual(parser(b"toggle", ""), "toggle")

    def test_json_payload(self) -> None:
        """The configured JSON key is extracted."""
        parser = _mqtt_parser()

        self.assertEqual(parser('{"action": "single"}', "action"), "single")

    def test_invalid_json_payload(self) -> None:
        """Invalid JSON and missing keys are ignored."""
        parser = _mqtt_parser()

        self.assertIsNone(parser("not-json", "action"))
        self.assertIsNone(parser('{"other": "single"}', "action"))
