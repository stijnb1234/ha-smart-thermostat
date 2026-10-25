"""Pure Vacation planning: periods from a calendar and from a manual start/return. No HA imports.

A Vacation period runs from its start to the moment the household is back. Calendar events
count when their title or description contains one of the keywords (every event when no
keywords are set, for a calendar kept for this). Overlapping or back-to-back periods merge.
The engine releases each Room one lead time before the return, so the house is warm then.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, time, tzinfo
from typing import Any

DEFAULT_KEYWORDS = ("vacation", "holiday", "vakantie")


@dataclass(frozen=True)
class VacationPeriod:
    start: datetime
    end: datetime

    def to_dict(self) -> dict[str, str]:
        return {"start": self.start.isoformat(), "end": self.end.isoformat()}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any] | None) -> VacationPeriod | None:
        try:
            start = datetime.fromisoformat(data["start"])  # type: ignore[index]
            end = datetime.fromisoformat(data["end"])  # type: ignore[index]
        except (KeyError, TypeError, ValueError):
            return None
        return cls(start, end) if start.tzinfo and end.tzinfo and start < end else None


def parse_keywords(text: str | None) -> tuple[str, ...]:
    """Comma-separated keywords as typed in the options; `*` (or blank) means every event counts."""
    keywords = tuple(k.strip().lower() for k in (text or "").split(",") if k.strip())
    return () if "*" in keywords else keywords


def _moment(value: Any, tz: tzinfo) -> datetime | None:
    """Calendar start/end: an ISO date (all-day, local midnight) or date-time."""
    if isinstance(value, Mapping):  # {"dateTime": ...} or {"date": ...} shapes
        value = value.get("dateTime") or value.get("date")
    if not isinstance(value, str):
        return None
    try:
        if len(value) == 10:
            return datetime.combine(date.fromisoformat(value), time(0), tzinfo=tz)
        moment = datetime.fromisoformat(value)
    except ValueError:
        return None
    return moment if moment.tzinfo else moment.replace(tzinfo=tz)


def periods_from_events(
    events: Iterable[Mapping[str, Any]], keywords: Sequence[str], tz: tzinfo
) -> list[VacationPeriod]:
    periods = []
    for event in events:
        text = f"{event.get('summary') or ''} {event.get('description') or ''}".lower()
        if keywords and not any(k in text for k in keywords):
            continue
        start, end = _moment(event.get("start"), tz), _moment(event.get("end"), tz)
        if start is not None and end is not None and start < end:
            periods.append(VacationPeriod(start, end))
    return periods


def merge(periods: Iterable[VacationPeriod]) -> list[VacationPeriod]:
    merged: list[VacationPeriod] = []
    for p in sorted(periods, key=lambda p: p.start):
        if merged and p.start <= merged[-1].end:
            merged[-1] = VacationPeriod(merged[-1].start, max(merged[-1].end, p.end))
        else:
            merged.append(p)
    return merged


class VacationPlanner:
    """Combines the manual period and calendar periods into the engine's `vacation_until`.

    After a period ends, `until` stays set while nobody is home yet (the engine then follows
    the schedule, so the house is warm on arrival) and clears once someone is home; a finished
    manual period is dropped then.
    """

    def __init__(self) -> None:
        self.manual: VacationPeriod | None = None
        self.calendar: list[VacationPeriod] = []
        self._ended: datetime | None = None

    def active(self, now: datetime) -> VacationPeriod | None:
        periods = [*self.calendar, *([self.manual] if self.manual else [])]
        return next((p for p in merge(periods) if p.start <= now < p.end), None)

    def upcoming(self, now: datetime) -> VacationPeriod | None:
        periods = [*self.calendar, *([self.manual] if self.manual else [])]
        return next((p for p in merge(periods) if p.start > now), None)

    def until(self, now: datetime, anyone_home: bool) -> datetime | None:
        period = self.active(now)
        if period is not None:
            self._ended = period.end
            return period.end
        if self.manual is not None and self.manual.end <= now and anyone_home:
            self.manual = None
        if self._ended is not None and not anyone_home:
            return self._ended
        self._ended = None
        return None
