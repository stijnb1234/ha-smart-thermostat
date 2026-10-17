"""Pure explanation of a Room's target: why it is what it is, and when it next changes.

Mirrors the engine's precedence (Boost > window-open pause > Vacation > Away >
schedule with pre-heat > setback). No Home Assistant imports.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal

from .engine import Decision, EngineInput, RoomConfig
from .engine.engine import lead_time_for, wants_comfort
from .engine.overrides import boosted_rooms
from .engine.presence import presence_setpoint

Reason = Literal["boost", "window", "vacation", "away", "pre_heat", "schedule", "setback"]
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
    now = inp.now
    target = decision.trv_setpoints[room.name]
    boost = inp.boosts.get(room.name)
    if room.name in boosted_rooms(inp.boosts, now) and boost is not None:
        end = boost.start + boost.duration
        return Explanation("boost", target, end, _schedule_target(room, inp, end))
    pause_end = decision.window_paused_until.get(room.name)
    if pause_end is not None:
        return Explanation("window", target, pause_end, _schedule_target(room, inp, pause_end))
    forced = presence_setpoint(room, inp)
    if forced is not None:
        if inp.vacation_until is not None:
            until = inp.vacation_until
            return Explanation("vacation", target, until, _schedule_target(room, inp, until))
        return Explanation("away", target)
    change = _next_schedule_change(room, inp, now)
    reason: Reason
    if wants_comfort(room, now, inp.learned):
        in_window = wants_comfort(room, now, {room.name: timedelta(0)})
        reason = "schedule" if in_window else "pre_heat"
    else:
        reason = "setback"
    return Explanation(
        reason,
        target,
        change,
        _schedule_target(room, inp, change) if change else None,
    )
