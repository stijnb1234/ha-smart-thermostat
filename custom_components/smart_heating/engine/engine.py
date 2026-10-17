from __future__ import annotations

from datetime import datetime, timedelta
from typing import Mapping

from .boiler import easycontrol_setpoint, has_demand
from .models import Decision, EngineInput, RoomConfig, ScheduleWindow


def _window_active(window: ScheduleWindow, now: datetime) -> bool:
    t = now.time()
    today = now.weekday()
    if window.start < window.end:
        return today in window.days and window.start <= t < window.end
    # Runs past midnight: evening part belongs to today, morning part to yesterday.
    return (today in window.days and t >= window.start) or (
        (today - 1) % 7 in window.days and t < window.end
    )


def lead_time_for(room: RoomConfig, learned: Mapping[str, object]) -> timedelta:
    """Pre-heat lead time for a room: the learned value if any, else the fixed one.

    This is the single place ticket 10 substitutes its learned estimate.
    """
    value = learned.get(room.name)
    return value if isinstance(value, timedelta) else room.lead_time


def _wants_comfort(
    room: RoomConfig, now: datetime, learned: Mapping[str, object]
) -> bool:
    """In a window now, or a window starts within the room's lead time."""
    ahead = now + lead_time_for(room, learned)
    return any(_window_active(w, now) or _window_active(w, ahead) for w in room.schedule)


def decide(inp: EngineInput) -> Decision:
    """Return desired TRV setpoints, EasyControl setpoint and alerts.

    Rooms are at comfort inside their schedule windows, otherwise at setback.
    The boiler call stays low until demand handling is added.
    """
    trv_setpoints = {
        room.name: room.comfort if _wants_comfort(room, inp.now, inp.learned) else room.setback
        for room in inp.config.rooms
    }
    demand = has_demand(inp.config, trv_setpoints, inp.room_temps)
    return Decision(
        trv_setpoints=trv_setpoints,
        easycontrol_setpoint=easycontrol_setpoint(inp, demand),
    )
