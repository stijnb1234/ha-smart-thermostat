"""Open-window detection: a rate-of-fall rule over Room temperature history."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Sequence

from .models import EPSILON, EngineInput, RoomConfig, SensorReading

MIN_PAUSE = timedelta(minutes=15)
MAX_PAUSE = timedelta(minutes=30)


def recent_drop(
    history: Sequence[SensorReading], now: datetime, period: timedelta
) -> float | None:
    """How far the latest reading is below the highest one within `period` (None: too few)."""
    cutoff = now - period
    recent = [r.value for r in history if cutoff <= r.at <= now]
    if len(recent) < 2:
        return None
    return max(recent) - recent[-1]


def drop_threshold(room: RoomConfig, inp: EngineInput) -> float:
    """The configured drop is the ceiling; a learned, lower value fits the Room's own noise."""
    return min(room.window_drop, inp.window_thresholds.get(room.name, room.window_drop))


def _fast_fall(room: RoomConfig, inp: EngineInput) -> bool:
    drop = recent_drop(inp.temp_history.get(room.name, ()), inp.now, room.window_period)
    return drop is not None and drop >= drop_threshold(room, inp) - EPSILON


def window_pauses(inp: EngineInput) -> dict[str, datetime]:
    """Rooms currently paused, mapped to when their pause ends."""
    paused: dict[str, datetime] = {}
    for room in inp.config.rooms:
        if not room.window_detection:
            continue
        until = inp.last_commands.window_paused_until.get(room.name)
        if until is not None and inp.now < until:
            paused[room.name] = until
        elif _fast_fall(room, inp):
            length = min(max(room.window_pause, MIN_PAUSE), MAX_PAUSE)
            paused[room.name] = inp.now + length
    return paused
