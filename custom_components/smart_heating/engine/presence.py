"""Away and Vacation mode: overrides of the schedule target (spec precedence:
Boost > window-open pause > Vacation > Away > schedule > setback)."""

from __future__ import annotations

from datetime import datetime

from .models import EngineInput, RoomConfig
from .schedule import lead_time_for


def vacation_release(room: RoomConfig, inp: EngineInput) -> datetime | None:
    """When the Room leaves Vacation mode: one lead time before the return, so it is warm then.

    The lead time is the Room's current one, which grows with how far it has cooled down."""
    if inp.vacation_until is None:
        return None
    return inp.vacation_until - lead_time_for(room, inp.learned)


def presence_setpoint(room: RoomConfig, inp: EngineInput) -> float | None:
    """Target forced by Vacation or Away, or None to follow the schedule."""
    release = vacation_release(room, inp)
    if release is not None:
        # Once released the schedule applies even if nobody is home yet, so rooms are warm on
        # arrival.
        return room.frost_hold if inp.now < release else None
    if inp.anyone_home:
        return None
    if inp.away_since is not None and inp.now - inp.away_since >= inp.config.prolonged_absence:
        return room.frost_hold
    return room.setback
