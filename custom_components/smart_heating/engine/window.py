"""Open-window detection: a rate-of-fall rule over Room temperature history."""

from __future__ import annotations

from datetime import datetime, timedelta

from .models import EPSILON, EngineInput, RoomConfig

MIN_PAUSE = timedelta(minutes=15)
MAX_PAUSE = timedelta(minutes=30)


def _fast_fall(room: RoomConfig, inp: EngineInput) -> bool:
    history = inp.temp_history.get(room.name, ())
    cutoff = inp.now - room.window_period
    recent = [r.value for r in history if cutoff <= r.at <= inp.now]
    if len(recent) < 2:
        return False
    return max(recent) - recent[-1] >= room.window_drop - EPSILON


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
