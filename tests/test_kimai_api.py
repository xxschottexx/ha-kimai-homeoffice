"""Tests for Kimai summary runtime values."""

from datetime import datetime, timedelta, timezone
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys
from types import ModuleType
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch

MODULE_NAME = "kimai_api_under_test"
if "aiohttp" not in sys.modules:
    aiohttp = ModuleType("aiohttp")
    aiohttp.ClientError = Exception
    sys.modules["aiohttp"] = aiohttp
MODULE_PATH = (
    Path(__file__).parents[1]
    / "custom_components"
    / "kimai_homeoffice"
    / "kimai_api.py"
)
SPEC = spec_from_file_location(MODULE_NAME, MODULE_PATH)
assert SPEC and SPEC.loader
KIMAI_API = module_from_spec(SPEC)
sys.modules[MODULE_NAME] = KIMAI_API
SPEC.loader.exec_module(KIMAI_API)
KimaiApi = KIMAI_API.KimaiApi


class KimaiSummaryRuntimeTest(IsolatedAsyncioTestCase):
    """Test active runtime values in Kimai summaries."""

    async def test_summary_without_active_timesheet(self) -> None:
        """Runtime is zero when no timesheet is active."""
        api = KimaiApi(AsyncMock(), "https://kimai.example", "token")
        api.active_timesheet = AsyncMock(return_value=None)
        api.duration_for_range = AsyncMock(return_value=5400)

        summary = await api.get_summary()

        self.assertEqual(summary.active_seconds, 0)
        self.assertEqual(summary.today_seconds, 5400)

    async def test_summary_runtime_uses_active_begin(self) -> None:
        """Runtime is calculated from the timezone-aware active begin time."""
        now = datetime(2026, 8, 16, 12, 0, tzinfo=timezone.utc)

        for elapsed in (timedelta(minutes=37), timedelta(hours=2, minutes=14)):
            with self.subTest(elapsed=elapsed):
                active = {
                    "id": 42,
                    "begin": (now - elapsed).isoformat(),
                    "end": None,
                }
                api = KimaiApi(AsyncMock(), "https://kimai.example", "token")
                api.active_timesheet = AsyncMock(return_value=active)
                api.duration_for_range = AsyncMock(return_value=0)

                with patch(
                    f"{MODULE_NAME}.datetime"
                ) as mocked_datetime:
                    mocked_datetime.now.side_effect = (
                        lambda tz=None: now.astimezone(tz)
                        if tz
                        else now.replace(tzinfo=None)
                    )
                    mocked_datetime.fromisoformat.side_effect = datetime.fromisoformat
                    summary = await api.get_summary()

                self.assertEqual(
                    summary.active_seconds,
                    int(elapsed.total_seconds()),
                )
