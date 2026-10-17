from __future__ import annotations

from datetime import datetime, timedelta
from typing import Mapping

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


def _select_temperature(
    room: RoomConfig, inp: EngineInput
) -> tuple[float | None, bool]:
    """Return (room temperature, whether it came from the external sensor)."""
    ext = inp.external_temps.get(room.name)
    if ext is not None and inp.now - ext.at < inp.config.sensors.external_stale_after:
        return ext.value, True
    trv = inp.trv_temps.get(room.name)
    if trv is not None:
        return trv.value + room.trv_offset, False
    return None, False


def _needs_push(room: str, value: float, inp: EngineInput) -> bool:
    cfg = inp.config.sensors
    last = inp.last_commands.external_temp_pushed.get(room)
    last_at = inp.last_commands.external_temp_pushed_at.get(room)
    if last is None or last_at is None:
        return True
    return (
        abs(value - last) >= cfg.push_threshold - 1e-9
        or inp.now - last_at >= cfg.push_max_interval
    )


def decide(inp: EngineInput) -> Decision:
    """Return desired TRV setpoints, EasyControl setpoint and alerts.

    Rooms are at comfort inside their schedule windows, otherwise at setback.
    The boiler call stays low until demand handling is added.
    """
    room_temps: dict[str, float] = {}
    pushes: dict[str, float] = {}
    for room in inp.config.rooms:
        temp, external = _select_temperature(room, inp)
        if temp is None:
            continue
        room_temps[room.name] = temp
        if external and _needs_push(room.name, temp, inp):
            pushes[room.name] = temp
    return Decision(
        trv_setpoints={
            room.name: room.comfort if _wants_comfort(room, inp.now, inp.learned) else room.setback
            for room in inp.config.rooms
        },
        easycontrol_setpoint=inp.config.easycontrol_low,
        room_temps=room_temps,
        external_temp_pushes=pushes,
    )
