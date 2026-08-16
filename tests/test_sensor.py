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
FUNCTION_NAMES = {
    "_seconds_to_hhmm",
    "_seconds_to_signed_hhmm",
    "_remaining_seconds",
    "_goal_seconds",
}
FORMAT_FUNCTIONS = [
    node
    for node in SENSOR_TREE.body
    if isinstance(node, ast.FunctionDef) and node.name in FUNCTION_NAMES
]
NAMESPACE: dict[str, object] = {}
exec(compile(ast.Module(FORMAT_FUNCTIONS, []), SENSOR_PATH, "exec"), NAMESPACE)
_seconds_to_hhmm = NAMESPACE["_seconds_to_hhmm"]
_seconds_to_signed_hhmm = NAMESPACE["_seconds_to_signed_hhmm"]
_remaining_seconds = NAMESPACE["_remaining_seconds"]
_goal_seconds = NAMESPACE["_goal_seconds"]


class RuntimeFormattingTest(TestCase):
    """Test runtime sensor formatting."""

    def test_runtime_formatting(self) -> None:
        """Runtime seconds are exposed as HH:MM values."""
        self.assertEqual(_seconds_to_hhmm(0), "00:00")
        self.assertEqual(_seconds_to_hhmm(37 * 60), "00:37")
        self.assertEqual(_seconds_to_hhmm((2 * 60 + 14) * 60), "02:14")


class GoalCalculationTest(TestCase):
    """Test daily and weekly goal calculations."""

    def test_daily_goal_balances_and_remaining_time(self) -> None:
        """Daily values are calculated against a seven-hour goal."""
        goal = _goal_seconds(7, 0)

        for worked, balance, remaining in (
            ((0, 0), "-07:00", "07:00"),
            ((6, 30), "-00:30", "00:30"),
            ((7, 0), "±00:00", "00:00"),
            ((7, 15), "+00:15", "00:00"),
        ):
            with self.subTest(worked=worked):
                worked_seconds = _goal_seconds(*worked)
                self.assertEqual(
                    _seconds_to_signed_hhmm(worked_seconds - goal),
                    balance,
                )
                self.assertEqual(
                    _seconds_to_hhmm(
                        _remaining_seconds(worked_seconds, goal)
                    ),
                    remaining,
                )

    def test_weekly_goal_balances(self) -> None:
        """Weekly values are calculated against a 35-hour goal."""
        goal = _goal_seconds(35, 0)

        for worked, balance in (
            ((26, 20), "-08:40"),
            ((35, 0), "±00:00"),
            ((36, 15), "+01:15"),
        ):
            with self.subTest(worked=worked):
                self.assertEqual(
                    _seconds_to_signed_hhmm(_goal_seconds(*worked) - goal),
                    balance,
                )
