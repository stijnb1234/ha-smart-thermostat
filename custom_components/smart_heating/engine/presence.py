"""Away and Vacation mode: overrides of the schedule target (spec precedence:
Boost > window-open pause > Vacation > Away > schedule > setback)."""

from __future__ import annotations

from datetime import datetime, timedelta

from .models import EngineInput, RoomConfig


def vacation_end(start: datetime, days: int) -> datetime:
    """When Vacation mode ends: the start of the arrival day (start + N days).

    Rooms are back on schedule (with pre-heat) from midnight, so they are warm
    when the household arrives that day.
    """
    arrival = start + timedelta(days=days)
    return arrival.replace(hour=0, minute=0, second=0, microsecond=0)


def presence_setpoint(room: RoomConfig, inp: EngineInput) -> float | None:
    """Target forced by Vacation or Away, or None to follow the schedule."""
    until = inp.vacation_until
    if until is not None:
        # Once Vacation has ended the schedule applies even if nobody is home
        # yet, so rooms are warm on arrival.
        return room.frost_hold if inp.now < until else None
    if inp.anyone_home:
        return None
    if inp.away_since is not None and inp.now - inp.away_since >= inp.config.prolonged_absence:
        return room.frost_hold
    return room.setback
