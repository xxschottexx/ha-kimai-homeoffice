"""Tests for Kimai sensor value formatting."""

import ast
from math import isfinite
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
NAMESPACE: dict[str, object] = {
    "Any": object,
    "isfinite": isfinite,
    "DAILY_GOAL_MODE_DISABLED": "disabled",
    "DAILY_GOAL_MODE_MANUAL_ENTITY": "manual_entity",
    "DAILY_GOAL_MODE_WORKED_DAYS_ONLY": "worked_days_only",
    "DAILY_GOAL_MODE_WEEKLY_PLAN": "weekly_plan",
}
exec(compile(ast.Module(FORMAT_FUNCTIONS, []), SENSOR_PATH, "exec"), NAMESPACE)
DAILY_GOAL_PATH = SENSOR_PATH.with_name("daily_goal.py")
DAILY_GOAL_TREE = ast.parse(DAILY_GOAL_PATH.read_text(encoding="utf-8"))
DAILY_GOAL_FUNCTIONS = [
    node
    for node in DAILY_GOAL_TREE.body
    if isinstance(node, ast.FunctionDef)
    and node.name in {"manual_goal_seconds", "resolve_daily_goal_seconds"}
]
exec(
    compile(ast.Module(DAILY_GOAL_FUNCTIONS, []), DAILY_GOAL_PATH, "exec"),
    NAMESPACE,
)
_seconds_to_hhmm = NAMESPACE["_seconds_to_hhmm"]
_seconds_to_signed_hhmm = NAMESPACE["_seconds_to_signed_hhmm"]
_remaining_seconds = NAMESPACE["_remaining_seconds"]
_goal_seconds = NAMESPACE["_goal_seconds"]
_round_seconds = NAMESPACE["_round_seconds"]
_resolve_daily_goal_seconds = NAMESPACE["resolve_daily_goal_seconds"]


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


class FlexibleDailyGoalTest(TestCase):
    """Test flexible daily goal modes."""

    def test_fixed_mode(self) -> None:
        """Fixed mode retains the existing daily goal behavior."""
        goal = _resolve_daily_goal_seconds(
            "fixed", True, _goal_seconds(7, 0), _goal_seconds(6, 30), 0
        )

        self.assertEqual(goal, _goal_seconds(7, 0))
        self.assertEqual(
            _seconds_to_signed_hhmm(_goal_seconds(6, 30) - goal),
            "-00:30",
        )
        self.assertEqual(
            _seconds_to_hhmm(_remaining_seconds(_goal_seconds(6, 30), goal)),
            "00:30",
        )

    def test_disabled_mode(self) -> None:
        """Disabled mode does not return a misleading fixed goal."""
        self.assertIsNone(
            _resolve_daily_goal_seconds(
                "disabled", True, _goal_seconds(7, 0), 0, 0
            )
        )
        self.assertIsNone(
            _resolve_daily_goal_seconds(
                "fixed", False, _goal_seconds(7, 0), 0, 0
            )
        )

    def test_weekly_plan(self) -> None:
        """Weekly planning uses planned days and current-day overrides."""
        fixed = _goal_seconds(7, 0)

        self.assertEqual(
            _resolve_daily_goal_seconds(
                "weekly_plan",
                True,
                fixed,
                0,
                0,
                planned_today=True,
                current_date="2026-08-17",
            ),
            fixed,
        )
        self.assertEqual(
            _resolve_daily_goal_seconds(
                "weekly_plan",
                True,
                fixed,
                0,
                0,
                planned_today=False,
                current_date="2026-08-18",
            ),
            0,
        )

    def test_weekly_plan_manual_override(self) -> None:
        """Only an override stored for the current date is applied."""
        fixed = _goal_seconds(7, 0)
        self.assertEqual(
            _resolve_daily_goal_seconds(
                "weekly_plan",
                True,
                fixed,
                0,
                0,
                planned_today=False,
                manual_override_hours=2.5,
                manual_override_date="2026-08-18",
                current_date="2026-08-18",
            ),
            _goal_seconds(2, 30),
        )
        self.assertEqual(
            _resolve_daily_goal_seconds(
                "weekly_plan",
                True,
                fixed,
                0,
                0,
                planned_today=True,
                manual_override_hours=2.5,
                manual_override_date="2026-08-18",
                current_date="2026-08-19",
            ),
            fixed,
        )
    def test_worked_days_only_mode(self) -> None:
        """The fixed goal applies only after work exists or tracking starts."""
        fixed = _goal_seconds(7, 0)
        self.assertIsNone(
            _resolve_daily_goal_seconds("worked_days_only", True, fixed, 0, 0)
        )

        for worked, active_id, expected_balance in (
            (_goal_seconds(2, 15), 0, "-04:45"),
            (_goal_seconds(0, 10), 42, "-06:50"),
        ):
            with self.subTest(worked=worked, active_id=active_id):
                goal = _resolve_daily_goal_seconds(
                    "worked_days_only", True, fixed, worked, active_id
                )
                self.assertEqual(goal, fixed)
                self.assertEqual(
                    _seconds_to_signed_hhmm(worked - goal),
                    expected_balance,
                )

    def test_manual_entity_mode(self) -> None:
        """Decimal entity hours become the active daily goal."""
        worked = _goal_seconds(2, 15)

        for state, expected_goal, balance, remaining in (
            ("2", _goal_seconds(2, 0), "+00:15", "00:00"),
            ("2.5", _goal_seconds(2, 30), "-00:15", "00:15"),
        ):
            with self.subTest(state=state):
                goal = _resolve_daily_goal_seconds(
                    "manual_entity", True, _goal_seconds(7, 0), worked, 0, state
                )
                self.assertEqual(goal, expected_goal)
                self.assertEqual(
                    _seconds_to_signed_hhmm(worked - goal),
                    balance,
                )
                self.assertEqual(
                    _seconds_to_hhmm(_remaining_seconds(worked, goal)),
                    remaining,
                )

        self.assertIsNone(
            _resolve_daily_goal_seconds(
                "manual_entity",
                True,
                _goal_seconds(7, 0),
                worked,
                0,
                "unknown",
            )
        )
