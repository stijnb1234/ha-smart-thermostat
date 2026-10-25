"""Comfort schedule: when a Room wants comfort, with pre-heat lead time."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timedelta

from .models import RoomConfig, ScheduleWindow


def _window_active(window: ScheduleWindow, now: datetime) -> bool:
    t = now.time()
    today = now.weekday()
    if window.start < window.end:
        return today in window.days and window.start <= t < window.end
    # Runs past midnight: evening part belongs to today, morning part to yesterday.
    return (today in window.days and t >= window.start) or (
        (today - 1) % 7 in window.days and t < window.end
    )


def lead_time_for(room: RoomConfig, learned: Mapping[str, timedelta]) -> timedelta:
    """Pre-heat lead time for a room: the learned value if any, else the fixed one."""
    return learned.get(room.name, room.lead_time)


def in_window(room: RoomConfig, now: datetime) -> bool:
    """Inside one of the room's comfort windows right now (no pre-heat)."""
    return any(_window_active(w, now) for w in room.schedule)


def wants_comfort(room: RoomConfig, now: datetime, learned: Mapping[str, timedelta]) -> bool:
    """In a window now, or a window starts within the room's lead time."""
    ahead = now + lead_time_for(room, learned)
    return any(_window_active(w, now) or _window_active(w, ahead) for w in room.schedule)
