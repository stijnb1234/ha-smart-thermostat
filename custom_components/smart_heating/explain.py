"""Pure explanation of a Room's target: why it is what it is, and when it next changes.

The reason comes from the engine (`Decision.reasons`); this module only adds
when the target next changes. No Home Assistant imports.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from .engine import Decision, EngineInput, RoomConfig, lead_time_for, vacation_release, wants_comfort
from .engine.models import Reason
from .i18n import DEFAULT_LANGUAGE, number, tr, weekday

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
    target = decision.hand_set.get(room.name, decision.trv_setpoints[room.name])
    reason = decision.reasons[room.name]
    end: datetime | None
    if reason == "boost":
        boost = inp.boosts[room.name]
        end = boost.start + boost.duration
    elif reason == "window":
        end = decision.window_paused_until[room.name]
    elif reason == "vacation":
        end = vacation_release(room, inp)
    elif reason in ("away", "occupant_away", "floor_first", "satisfied"):
        return Explanation(reason, target)
    else:
        change = _next_schedule_change(room, inp, inp.now)
        return Explanation(
            reason, target, change, _schedule_target(room, inp, change) if change else None
        )
    assert end is not None
    return Explanation(reason, target, end, _schedule_target(room, inp, end))


def _degrees(value: float, lang: str = DEFAULT_LANGUAGE) -> str:
    return tr(lang, "degrees", value=number(value, lang))


def _when(at: datetime, now: datetime, lang: str = DEFAULT_LANGUAGE) -> str:
    """Clock time for today, weekday and time for later days (`at` and `now` in local time)."""
    clock = at.strftime("%H:%M")
    return clock if at.date() == now.date() else f"{weekday(lang, at.weekday())} {clock}"


def summarize(e: Explanation, now: datetime, lang: str = DEFAULT_LANGUAGE) -> str:
    """One plain sentence for the dashboard; the reason sensor stays the machine value."""
    end = _when(e.next_change_at, now, lang) if e.next_change_at else None
    temp = _degrees(e.target, lang)
    fixed = {"away", "occupant_away", "floor_first", "satisfied"}
    if e.reason in fixed:
        return tr(lang, f"summary.{e.reason}", temp=temp)
    key = e.reason if end else f"{e.reason}_open"
    if e.reason == "setback":
        key = "setback" if end else "setback_open"
    return tr(lang, f"summary.{key}", end=end, temp=temp)
