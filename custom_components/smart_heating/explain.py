"""Pure explanation of a Room's target: why it is what it is, and when it next changes.

The reason comes from the engine (`Decision.reasons`); this module only adds
when the target next changes. No Home Assistant imports.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from .engine import Decision, EngineInput, RoomConfig, lead_time_for, wants_comfort
from .engine.models import Reason

_HORIZON_DAYS = 8


@dataclass(frozen=True)
class Explanation:
    reason: Reason
    target: float
    next_change_at: datetime | None = None
    next_change_target: float | None = None


def _schedule_target(room: RoomConfig, inp: EngineInput, at: datetime) -> float:
    return room.comfort if wants_comfort(room, at, inp.learned) else room.setback


def _next_schedule_change(room: RoomConfig, inp: EngineInput, after: datetime) -> datetime | None:
    """First moment after `after` at which the schedule target (with pre-heat) flips."""
    lead = lead_time_for(room, inp.learned)
    current = wants_comfort(room, after, inp.learned)
    candidates: list[datetime] = []
    for offset in range(-1, _HORIZON_DAYS):
        day = (after + timedelta(days=offset)).date()
        for window in room.schedule:
            for edge in (window.start, window.end):
                at = datetime.combine(day, edge, tzinfo=after.tzinfo)
                candidates += [at, at - lead]
    for at in sorted(c for c in set(candidates) if c > after):
        if wants_comfort(room, at, inp.learned) != current:
            return at
    return None


def explain(room: RoomConfig, inp: EngineInput, decision: Decision) -> Explanation:
    target = decision.trv_setpoints[room.name]
    reason = decision.reasons[room.name]
    end: datetime | None
    if reason == "boost":
        boost = inp.boosts[room.name]
        end = boost.start + boost.duration
    elif reason == "window":
        end = decision.window_paused_until[room.name]
    elif reason == "vacation":
        end = inp.vacation_until
    elif reason == "away":
        return Explanation(reason, target)
    else:
        change = _next_schedule_change(room, inp, inp.now)
        return Explanation(
            reason, target, change, _schedule_target(room, inp, change) if change else None
        )
    assert end is not None
    return Explanation(reason, target, end, _schedule_target(room, inp, end))


def _degrees(value: float) -> str:
    return f"{value:g} degrees"


def _when(at: datetime, now: datetime) -> str:
    """Clock time for today, weekday and time for later days (`at` and `now` in local time)."""
    return at.strftime("%H:%M") if at.date() == now.date() else at.strftime("%a %H:%M")


def summarize(e: Explanation, now: datetime) -> str:
    """One plain sentence for the dashboard; the reason sensor stays the machine value."""
    end = _when(e.next_change_at, now) if e.next_change_at else None
    if e.reason == "boost":
        return f"Boost until {end}" if end else "Boost"
    if e.reason == "window":
        return f"Window seems open, heating paused until {end}" if end else "Window seems open"
    if e.reason == "vacation":
        until = f"Vacation until {end}" if end else "Vacation"
        return f"{until}, kept at {_degrees(e.target)}"
    if e.reason == "away":
        return f"Nobody home, kept at {_degrees(e.target)}"
    if e.reason == "pre_heat":
        return f"Warming up, warm until {end}" if end else "Warming up"
    if e.reason == "schedule":
        return f"Warm until {end}" if end else "Warm"
    return f"Warm from {end}" if end else f"Kept at {_degrees(e.target)}"
