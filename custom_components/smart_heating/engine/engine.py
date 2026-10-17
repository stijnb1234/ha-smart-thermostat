from __future__ import annotations

from datetime import datetime, timedelta
from typing import Mapping

from .alerts import compute_alerts
from .boiler import demand_rooms, easycontrol_setpoint
from .trv import check_trvs
from .models import EPSILON, Decision, EngineInput, Reason, RoomConfig, ScheduleWindow
from .overrides import boosted_rooms, manual_override_active
from .presence import presence_setpoint
from .sensors import select_temperature
from .window import window_pauses


def _window_active(window: ScheduleWindow, now: datetime) -> bool:
    t = now.time()
    today = now.weekday()
    if window.start < window.end:
        return today in window.days and window.start <= t < window.end
    # Runs past midnight: evening part belongs to today, morning part to yesterday.
    return (today in window.days and t >= window.start) or (
        (today - 1) % 7 in window.days and t < window.end
    )


def lead_time_for(room: RoomConfig, learned: Mapping[str, timedelta]) -> timedelta:
    """Pre-heat lead time for a room: the learned value if any, else the fixed one."""
    return learned.get(room.name, room.lead_time)


def in_window(room: RoomConfig, now: datetime) -> bool:
    """Inside one of the room's comfort windows right now (no pre-heat)."""
    return any(_window_active(w, now) for w in room.schedule)


def wants_comfort(room: RoomConfig, now: datetime, learned: Mapping[str, timedelta]) -> bool:
    """In a window now, or a window starts within the room's lead time."""
    ahead = now + lead_time_for(room, learned)
    return any(_window_active(w, now) or _window_active(w, ahead) for w in room.schedule)


def _needs_push(room: str, value: float, inp: EngineInput) -> bool:
    cfg = inp.config.sensors
    last = inp.last_commands.external_temp_pushed.get(room)
    last_at = inp.last_commands.external_temp_pushed_at.get(room)
    if last is None or last_at is None:
        return True
    return (
        abs(value - last) >= cfg.push_threshold - EPSILON
        or inp.now - last_at >= cfg.push_max_interval
    )


def _target(
    room: RoomConfig,
    inp: EngineInput,
    boosted: frozenset[str],
    paused: Mapping[str, datetime],
) -> tuple[float, Reason]:
    """The precedence ladder: Boost > window-open pause > Vacation > Away > schedule > setback."""
    if room.name in boosted:
        return room.comfort, "boost"
    if room.name in paused:
        return room.frost_hold, "window"
    forced = presence_setpoint(room, inp)
    if forced is not None:
        return forced, "vacation" if inp.vacation_until is not None else "away"
    if wants_comfort(room, inp.now, inp.learned):
        return room.comfort, "schedule" if in_window(room, inp.now) else "pre_heat"
    return room.setback, "setback"


def decide(inp: EngineInput) -> Decision:
    """Return desired TRV setpoints with reasons, EasyControl setpoint and alerts.

    The EasyControl call is raised while a Room heating to comfort has unmet demand
    (or a Manual-room override is active) and lowered otherwise, subject to the
    debounce/backoff policy. A Bosch outage only throttles EasyControl writes and
    raises an alert; TRV control is independent of the Bosch cloud.
    """
    room_temps: dict[str, float] = {}
    pushes: dict[str, float] = {}
    for room in inp.config.rooms:
        temp, external = select_temperature(
            room, inp.external_temps, inp.trv_temps, inp.now, inp.config.sensors
        )
        if temp is None:
            continue
        room_temps[room.name] = temp
        if external and _needs_push(room.name, temp, inp):
            pushes[room.name] = temp
    boosted = boosted_rooms(inp.boosts, inp.now)
    paused = {k: v for k, v in window_pauses(inp).items() if k not in boosted}
    trv_setpoints: dict[str, float] = {}
    reasons: dict[str, Reason] = {}
    for room in inp.config.rooms:
        trv_setpoints[room.name], reasons[room.name] = _target(room, inp, boosted, paused)
    calling = demand_rooms(inp.config, trv_setpoints, room_temps)
    demand = bool(calling) or manual_override_active(
        inp.manual_overrides, inp.now
    )
    ec_setpoint, reassert, ec_hold = easycontrol_setpoint(inp, demand)
    trv = check_trvs(inp, trv_setpoints)
    return Decision(
        trv_setpoints=trv_setpoints,
        easycontrol_setpoint=ec_setpoint,
        easycontrol_reassert=reassert,
        easycontrol_hold_until=ec_hold,
        trv_rewrite=trv.rewrite,
        trv_manual=trv.manual,
        trv_retries=trv.retries,
        reasons=reasons,
        alerts=(*compute_alerts(inp), *trv.alerts),
        room_temps=room_temps,
        external_temp_pushes=pushes,
        window_paused_until=paused,
        demand_rooms=calling,
    )
