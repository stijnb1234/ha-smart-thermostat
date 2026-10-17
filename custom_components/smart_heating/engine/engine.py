from __future__ import annotations

from datetime import datetime, timedelta
from typing import Mapping

from .alerts import bosch_outage, compute_alerts
from .boiler import easycontrol_setpoint, has_demand
from .window import window_pauses
from .models import Decision, EngineInput, RoomConfig, ScheduleWindow
from .overrides import boosted_rooms, manual_override_active
from .presence import presence_setpoint


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


def wants_comfort(
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
    boosted = boosted_rooms(inp.boosts, inp.now)  # top precedence
    trv_setpoints = {}
    for room in inp.config.rooms:
        forced = presence_setpoint(room, inp)
        if room.name in boosted:
            trv_setpoints[room.name] = room.comfort
        elif forced is not None:
            trv_setpoints[room.name] = forced
        elif wants_comfort(room, inp.now, inp.learned):
            trv_setpoints[room.name] = room.comfort
        else:
            trv_setpoints[room.name] = room.setback
    # Precedence: Boost > window-open pause > Vacation > Away > schedule > setback.
    paused = {k: v for k, v in window_pauses(inp).items() if k not in boosted}
    for room in inp.config.rooms:
        if room.name in paused:
            trv_setpoints[room.name] = room.frost_hold
    demand = has_demand(inp.config, trv_setpoints, room_temps) or manual_override_active(
        inp.manual_overrides, inp.now
    )
    ec_setpoint = easycontrol_setpoint(inp, demand)
    if bosch_outage(inp):
        # Safe fallback: TRVs keep their last setpoints. EasyControl writes stay
        # throttled by the backoff in boiler.py, which doubles as the recovery probe.
        trv_setpoints = {**trv_setpoints, **inp.last_commands.trv_setpoints}
    return Decision(
        trv_setpoints=trv_setpoints,
        easycontrol_setpoint=ec_setpoint,
        alerts=compute_alerts(inp),
        room_temps=room_temps,
        external_temp_pushes=pushes,
        window_paused_until=paused,
    )
