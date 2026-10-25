"""Pure per-Room learned behaviour next to the pre-heat lead time. No Home Assistant imports.

Four things are learned per Room, each with a safe fallback while data is thin:
  - how far the temperature normally falls within the window-detection period (quiet
    samples), so the open-window threshold fits the Room's own noise;
  - how far a Room keeps rising after it stops calling for heat (coast), so the call
    can end early enough not to overshoot;
  - how the external sensor differs from the TRV sensor while the radiator is idle;
  - when someone boosts or turns up a Room outside its schedule (schedule suggestions).
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from statistics import median
from typing import Any, Callable, Mapping

SCHEMA_VERSION = 1

MAX_DROP_SAMPLES = 576  # two days at one sample per five minutes
MIN_DROP_SAMPLES = 36  # three hours of quiet
WINDOW_MARGIN = 0.4  # K above the Room's 95th-percentile quiet fall
MIN_WINDOW_DROP = 0.5

MAX_COAST_SAMPLES = 10
MIN_COAST_SAMPLES = 3
MAX_COAST = 1.0

MAX_OFFSET_SAMPLES = 200
MIN_OFFSET_SAMPLES = 24
MAX_OFFSET = 5.0

EVENT_KEEP = timedelta(days=28)
MAX_EVENTS = 200
MIN_EVENT_DATES = 3
CLUSTER_SPAN = 45  # minutes within which events count as the same habit


@dataclass(frozen=True)
class Suggestion:
    """A recurring manual wish for warmth that the Room's schedule does not cover."""

    room: str
    days: tuple[int, ...]
    start: time
    events: int


def _percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    return ordered[min(int(q * len(ordered)), len(ordered) - 1)]


def _clamp(value: float, low: float, high: float) -> float:
    return min(max(value, low), high)


class RoomInsights:
    def __init__(self) -> None:
        self._drops: dict[str, deque[float]] = {}
        self._coasts: dict[str, deque[float]] = {}
        self._offsets: dict[str, deque[float]] = {}
        self._events: dict[str, list[datetime]] = {}

    # --- open-window threshold -------------------------------------------------
    def record_drop(self, room: str, drop: float) -> None:
        self._drops.setdefault(room, deque(maxlen=MAX_DROP_SAMPLES)).append(max(drop, 0.0))

    def window_threshold(self, room: str, cap: float) -> float | None:
        """Learned drop that signals an open window, never above the configured `cap`."""
        samples = self._drops.get(room)
        if not samples or len(samples) < MIN_DROP_SAMPLES:
            return None
        return _clamp(_percentile(list(samples), 0.95) + WINDOW_MARGIN, MIN_WINDOW_DROP, max(cap, MIN_WINDOW_DROP))

    # --- coast after a call ends -------------------------------------------------
    def record_coast(self, room: str, rise: float) -> None:
        self._coasts.setdefault(room, deque(maxlen=MAX_COAST_SAMPLES)).append(max(rise, 0.0))

    def coast(self, room: str) -> float | None:
        samples = self._coasts.get(room)
        if not samples or len(samples) < MIN_COAST_SAMPLES:
            return None
        return _clamp(median(samples), 0.0, MAX_COAST)

    # --- external vs TRV sensor ----------------------------------------------------
    def record_offset(self, room: str, external_minus_trv: float) -> None:
        self._offsets.setdefault(room, deque(maxlen=MAX_OFFSET_SAMPLES)).append(external_minus_trv)

    def offset(self, room: str) -> float | None:
        samples = self._offsets.get(room)
        if not samples or len(samples) < MIN_OFFSET_SAMPLES:
            return None
        return _clamp(median(samples), -MAX_OFFSET, MAX_OFFSET)

    # --- schedule suggestions ------------------------------------------------------
    def record_event(self, room: str, at: datetime) -> None:
        events = self._events.setdefault(room, [])
        events.append(at)
        del events[:-MAX_EVENTS]

    def suggestions(
        self, now: datetime, covered: Callable[[str, datetime], bool]
    ) -> list[Suggestion]:
        """Habits seen on at least three different days within four weeks, not yet scheduled.

        `covered(room, at)` says whether the Room's schedule already has comfort at that moment.
        """
        found: list[Suggestion] = []
        for room, events in self._events.items():
            recent = sorted(
                (e for e in events if now - e <= EVENT_KEEP and not covered(room, e)),
                key=lambda e: e.hour * 60 + e.minute,
            )
            clusters: list[list[datetime]] = []
            for event in recent:
                minute = event.hour * 60 + event.minute
                if clusters and minute - _minute(clusters[-1][0]) <= CLUSTER_SPAN:
                    clusters[-1].append(event)
                else:
                    clusters.append([event])
            for cluster in clusters:
                if len({e.date() for e in cluster}) < MIN_EVENT_DATES:
                    continue
                minutes = round(median(_minute(e) for e in cluster) / 5) * 5
                found.append(
                    Suggestion(
                        room,
                        tuple(sorted({e.weekday() for e in cluster})),
                        time(minutes // 60 % 24, minutes % 60),
                        len(cluster),
                    )
                )
        return found

    # --- persistence -----------------------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return {
            "version": SCHEMA_VERSION,
            "drops": {r: list(v) for r, v in self._drops.items()},
            "coasts": {r: list(v) for r, v in self._coasts.items()},
            "offsets": {r: list(v) for r, v in self._offsets.items()},
            "events": {r: [e.isoformat() for e in v] for r, v in self._events.items()},
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any] | None) -> RoomInsights:
        insights = cls()
        if not data or data.get("version") != SCHEMA_VERSION:
            return insights
        try:
            for attr, key, size in (
                ("_drops", "drops", MAX_DROP_SAMPLES),
                ("_coasts", "coasts", MAX_COAST_SAMPLES),
                ("_offsets", "offsets", MAX_OFFSET_SAMPLES),
            ):
                setattr(
                    insights,
                    attr,
                    {r: deque((float(x) for x in v), maxlen=size) for r, v in data.get(key, {}).items()},
                )
            insights._events = {
                r: [datetime.fromisoformat(e) for e in v] for r, v in data.get("events", {}).items()
            }
        except (TypeError, ValueError, AttributeError):
            return cls()
        return insights


def _minute(at: datetime) -> int:
    return at.hour * 60 + at.minute
