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
    "_round_seconds",
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
_round_seconds = NAMESPACE["_round_seconds"]


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


class TimeRoundingTest(TestCase):
    """Test configurable display time rounding."""

    def test_ceil_five_minutes(self) -> None:
        """Ceil rounds positive values up to the next interval."""
        for raw_minutes, expected_minutes in (
            (0, 0),
            (1, 5),
            (4, 5),
            (5, 5),
            (7 * 60 + 21, 7 * 60 + 25),
            (7 * 60 + 23, 7 * 60 + 25),
            (7 * 60 + 25, 7 * 60 + 25),
        ):
            with self.subTest(raw_minutes=raw_minutes):
                self.assertEqual(
                    _round_seconds(raw_minutes * 60, 5, "ceil"),
                    expected_minutes * 60,
                )

    def test_floor_five_minutes(self) -> None:
        """Floor rounds positive values down to the previous interval."""
        for raw_minutes, expected_minutes in (
            (1, 0),
            (4, 0),
            (5, 5),
            (7 * 60 + 21, 7 * 60 + 20),
            (7 * 60 + 23, 7 * 60 + 20),
            (7 * 60 + 25, 7 * 60 + 25),
        ):
            with self.subTest(raw_minutes=raw_minutes):
                self.assertEqual(
                    _round_seconds(raw_minutes * 60, 5, "floor"),
                    expected_minutes * 60,
                )

    def test_nearest_five_minutes(self) -> None:
        """Nearest rounds mathematically to the closest interval."""
        for raw_minutes, expected_minutes in (
            (7 * 60 + 21, 7 * 60 + 20),
            (7 * 60 + 22, 7 * 60 + 20),
            (7 * 60 + 23, 7 * 60 + 25),
            (7 * 60 + 25, 7 * 60 + 25),
        ):
            with self.subTest(raw_minutes=raw_minutes):
                self.assertEqual(
                    _round_seconds(raw_minutes * 60, 5, "nearest"),
                    expected_minutes * 60,
                )

    def test_invalid_values_are_safe(self) -> None:
        """Non-positive inputs and invalid intervals do not crash."""
        self.assertEqual(_round_seconds(-60, 5, "ceil"), 0)
        self.assertEqual(_round_seconds(60, 0, "ceil"), 60)
        self.assertEqual(_round_seconds(60, 5, "unknown"), 300)

    def test_daily_goal_uses_rounded_today(self) -> None:
        """Daily balance and remaining time use the rounded work value."""
        goal = _goal_seconds(7, 0)

        for raw, rounded, balance, remaining in (
            ((6, 51), (6, 55), "-00:05", "00:05"),
            ((6, 56), (7, 0), "±00:00", "00:00"),
            ((7, 21), (7, 25), "+00:25", "00:00"),
        ):
            with self.subTest(raw=raw):
                rounded_seconds = _round_seconds(_goal_seconds(*raw), 5, "ceil")
                self.assertEqual(rounded_seconds, _goal_seconds(*rounded))
                self.assertEqual(
                    _seconds_to_signed_hhmm(rounded_seconds - goal),
                    balance,
                )
                self.assertEqual(
                    _seconds_to_hhmm(
                        _remaining_seconds(rounded_seconds, goal)
                    ),
                    remaining,
                )
