"""Tests for Kimai sensor value formatting."""

import ast
from pathlib import Path
from unittest import TestCase


SENSOR_PATH = (
    Path(__file__).parents[1]
    / "custom_components"
    / "kimai_homeoffice"
    / "sensor.py"
)
SENSOR_TREE = ast.parse(SENSOR_PATH.read_text(encoding="utf-8"))
FORMAT_FUNCTION = next(
    node
    for node in SENSOR_TREE.body
    if isinstance(node, ast.FunctionDef) and node.name == "_seconds_to_hhmm"
)
NAMESPACE: dict[str, object] = {}
exec(compile(ast.Module([FORMAT_FUNCTION], []), SENSOR_PATH, "exec"), NAMESPACE)
_seconds_to_hhmm = NAMESPACE["_seconds_to_hhmm"]


class RuntimeFormattingTest(TestCase):
    """Test runtime sensor formatting."""

    def test_runtime_formatting(self) -> None:
        """Runtime seconds are exposed as HH:MM values."""
        self.assertEqual(_seconds_to_hhmm(0), "00:00")
        self.assertEqual(_seconds_to_hhmm(37 * 60), "00:37")
        self.assertEqual(_seconds_to_hhmm((2 * 60 + 14) * 60), "02:14")
