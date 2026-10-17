from __future__ import annotations

from datetime import datetime

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


def _wants_comfort(room: RoomConfig, now: datetime) -> bool:
    return any(_window_active(w, now) for w in room.schedule)


def decide(inp: EngineInput) -> Decision:
    """Return desired TRV setpoints, EasyControl setpoint and alerts.

    Rooms are at comfort inside their schedule windows, otherwise at setback.
    The boiler call stays low until demand handling is added.
    """
    return Decision(
        trv_setpoints={
            room.name: room.comfort if _wants_comfort(room, inp.now) else room.setback
            for room in inp.config.rooms
        },
        easycontrol_setpoint=inp.config.easycontrol_low,
    )
