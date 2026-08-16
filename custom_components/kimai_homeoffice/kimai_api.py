"""Async Kimai API client for Kimai Homeoffice."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import aiohttp


class KimaiApiError(Exception):
    """Generic Kimai API error."""


class KimaiAuthError(KimaiApiError):
    """Kimai authentication error."""


class KimaiConnectionError(KimaiApiError):
    """Kimai connection error."""


@dataclass
class KimaiSummary:
    """Summary data from Kimai."""

    active_id: int = 0
    active_begin: str | None = None
    active_seconds: int = 0
    today_seconds: int = 0
    week_seconds: int = 0
    month_seconds: int = 0


def _html5_datetime(value: datetime) -> str:
    """Return Kimai-compatible HTML5 local datetime."""
    return value.replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%S")


def _now_html5() -> str:
    """Return current local datetime in Kimai-compatible format."""
    return _html5_datetime(datetime.now())


def _parse_datetime(value: Any) -> datetime | None:
    """Parse Kimai datetime value."""
    if not value:
        return None

    text = str(value)

    if text.endswith("Z"):
        text = text[:-1] + "+00:00"

    try:
        return datetime.fromisoformat(text)
    except ValueError:
        try:
            return datetime.strptime(text[:19], "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            return None


def _duration_seconds(item: dict[str, Any]) -> int:
    """Calculate duration in seconds for one Kimai timesheet."""
    duration = item.get("duration")

    if isinstance(duration, int) and duration > 0:
        return duration

    if isinstance(duration, float) and duration > 0:
        return int(duration)

    begin = _parse_datetime(item.get("begin"))
    end = _parse_datetime(item.get("end"))

    if not begin:
        return 0

    if end:
        return max(0, int((end - begin).total_seconds()))

    now = datetime.now(begin.tzinfo) if begin.tzinfo else datetime.now()
    return max(0, int((now - begin).total_seconds()))


class KimaiApi:
    """Small async API client for Kimai."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        base_url: str,
        api_token: str,
    ) -> None:
        """Initialize API client."""
        self._session = session
        self._base_url = base_url.rstrip("/")
        self._api_token = api_token.replace("Bearer ", "").strip()

    @property
    def headers(self) -> dict[str, str]:
        """Return request headers."""
        return {
            "Authorization": f"Bearer {self._api_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _url(self, path: str) -> str:
        """Build full API URL."""
        if not path.startswith("/"):
            path = f"/{path}"
        return f"{self._base_url}{path}"

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> Any:
        """Send request to Kimai."""
        url = self._url(path)

        try:
            async with self._session.request(
                method,
                url,
                headers=self.headers,
                params=params,
                json=json,
            ) as response:
                if response.status in (401, 403):
                    raise KimaiAuthError("Kimai token ungültig oder Zugriff verweigert")

                if response.status >= 400:
                    text = await response.text()
                    raise KimaiApiError(
                        f"Kimai API Fehler {response.status}: {text}"
                    )

                if response.status == 204:
                    return None

                try:
                    return await response.json(content_type=None)
                except Exception:
                    text = await response.text()
                    return text if text else None

        except aiohttp.ClientError as err:
            raise KimaiConnectionError(f"Kimai nicht erreichbar: {err}") from err

    async def get_user(self) -> dict[str, Any]:
        """Return current Kimai user."""
        return await self._request("GET", "/api/users/me")

    async def list_projects(self) -> list[dict[str, Any]]:
        """Return visible Kimai projects."""
        data = await self._request(
            "GET",
            "/api/projects",
            params={"visible": "1"},
        )

        if isinstance(data, list):
            return data

        if isinstance(data, dict):
            return data.get("hydra:member", [])

        return []

    async def list_activities(
        self,
        project_id: int | None = None,
    ) -> list[dict[str, Any]]:
        """Return visible Kimai activities."""
        params: dict[str, Any] = {"visible": "1"}

        if project_id is not None:
            params["project"] = int(project_id)

        data = await self._request(
            "GET",
            "/api/activities",
            params=params,
        )

        if isinstance(data, list):
            return data

        if isinstance(data, dict):
            return data.get("hydra:member", [])

        return []

    async def active_timesheets(self) -> list[dict[str, Any]]:
        """Return active Kimai timesheets."""
        data = await self._request("GET", "/api/timesheets/active")

        if isinstance(data, list):
            return data

        if isinstance(data, dict):
            return data.get("hydra:member", [])

        return []

    async def active_timesheet(self) -> dict[str, Any] | None:
        """Return first active Kimai timesheet."""
        active = await self.active_timesheets()
        return active[0] if active else None

    async def active_id(self) -> int:
        """Return active Kimai timesheet ID or 0."""
        active = await self.active_timesheet()

        if not active:
            return 0

        return int(active.get("id", 0))

    async def start_timesheet(
        self,
        project_id: int,
        activity_id: int,
    ) -> dict[str, Any]:
        """Start a new Kimai timesheet."""
        payload = {
            "begin": _now_html5(),
            "project": int(project_id),
            "activity": int(activity_id),
        }

        return await self._request(
            "POST",
            "/api/timesheets",
            json=payload,
        )

    async def stop_timesheet(
        self,
        timesheet_id: int | None = None,
    ) -> bool:
        """Stop a Kimai timesheet and return whether one was stopped."""
        if timesheet_id is None or int(timesheet_id) <= 0:
            active = await self.active_timesheet()

            if not active:
                return False

            timesheet_id = int(active["id"])

        await self._request(
            "PATCH",
            f"/api/timesheets/{int(timesheet_id)}/stop",
        )
        return True

    async def get_timesheets(
        self,
        begin: datetime,
        end: datetime,
    ) -> list[dict[str, Any]]:
        """Return timesheets for a time range."""
        data = await self._request(
            "GET",
            "/api/timesheets",
            params={
                "begin": _html5_datetime(begin),
                "end": _html5_datetime(end),
            },
        )

        if isinstance(data, list):
            return data

        if isinstance(data, dict):
            return data.get("hydra:member", [])

        return []

    async def duration_for_range(
        self,
        begin: datetime,
        end: datetime,
    ) -> int:
        """Return total duration in seconds for a time range."""
        entries = await self.get_timesheets(begin, end)
        return sum(_duration_seconds(entry) for entry in entries)

    async def get_summary(self) -> KimaiSummary:
        """Return active state and duration summary."""
        now = datetime.now()

        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow_start = today_start + timedelta(days=1)

        week_start = today_start - timedelta(days=today_start.weekday())
        week_end = week_start + timedelta(days=7)

        month_start = today_start.replace(day=1)

        if month_start.month == 12:
            month_end = month_start.replace(
                year=month_start.year + 1,
                month=1,
                day=1,
            )
        else:
            month_end = month_start.replace(month=month_start.month + 1, day=1)

        active = await self.active_timesheet()

        active_id = 0
        active_begin = None
        active_seconds = 0

        if active:
            active_id = int(active.get("id", 0))
            active_begin = active.get("begin")
            active_seconds = _duration_seconds(active)

        today_seconds = await self.duration_for_range(today_start, tomorrow_start)
        week_seconds = await self.duration_for_range(week_start, week_end)
        month_seconds = await self.duration_for_range(month_start, month_end)

        return KimaiSummary(
            active_id=active_id,
            active_begin=active_begin,
            active_seconds=active_seconds,
            today_seconds=today_seconds,
            week_seconds=week_seconds,
            month_seconds=month_seconds,
        )
