from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime

from .alerts import compute_alerts
from .boiler import boiler_setpoint, demand_rooms, room_hysteresis
from .compensation import trv_writes
from .models import EPSILON, Decision, EngineInput, Reason, RoomConfig
from .overrides import boosted_rooms, manual_override_active
from .presence import presence_setpoint
from .schedule import in_window, wants_comfort
from .sensors import select_temperature
from .trv import check_trvs
from .window import window_pauses


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
    """The precedence ladder: Boost > window-open pause > Vacation > Away > schedule > setback.

    A scheduled comfort period (incl. pre-heat) drops to setback while the room's occupants are away."""
    if room.name in boosted:
        return room.comfort, "boost"
    if room.name in paused:
        return room.frost_hold, "window"
    forced = presence_setpoint(room, inp)
    if forced is not None:
        return forced, "vacation" if inp.vacation_until is not None else "away"
    if wants_comfort(room, inp.now, inp.learned):
        if room.name in inp.absent_rooms:
            return room.setback, "occupant_away"
        return room.comfort, "schedule" if in_window(room, inp.now) else "pre_heat"
    return room.setback, "setback"


def _floor_first(
    inp: EngineInput,
    trv_setpoints: dict[str, float],
    reasons: dict[str, Reason],
    room_temps: Mapping[str, float],
) -> None:
    """While a floor-heating room pre-heats and is still cold, rooms that need no warmth stay shut.

    The floor loops are always open, so radiators at setback would compete for the flow;
    they drop to frost-hold until the floor has caught up.
    """
    busy = any(
        room.floor_heating
        and reasons[room.name] == "pre_heat"
        and room.name in room_temps
        and room_temps[room.name] < trv_setpoints[room.name] - room_hysteresis(inp.config, room)
        for room in inp.config.rooms
    )
    if not busy:
        return
    for room in inp.config.rooms:
        if not room.floor_heating and reasons[room.name] in ("setback", "away", "occupant_away"):
            trv_setpoints[room.name] = room.frost_hold
            reasons[room.name] = "floor_first"


def _open_radiators_capping(inp: EngineInput, room_temps: Mapping[str, float]) -> frozenset[str]:
    """Open-radiator Rooms that stop every boiler call: from reaching comfort until they have
    cooled more than the demand hysteresis below it, so the call does not flap at the edge."""
    before = inp.last_commands.open_radiators_capping
    capping = set()
    for room in inp.config.rooms:
        temp = room_temps.get(room.name)
        if not room.open_radiators or temp is None:
            continue
        threshold = room.comfort - (room_hysteresis(inp.config, room) if room.name in before else 0.0)
        if temp >= threshold - EPSILON:
            capping.add(room.name)
    return frozenset(capping)


def decide(inp: EngineInput) -> Decision:
    """Return desired TRV setpoints with reasons, boiler thermostat setpoint and alerts.

    The boiler call is raised while a Room heating to comfort has unmet demand
    (or a Manual-room override is active) and lowered otherwise, subject to the
    debounce/backoff policy. An outage only throttles boiler thermostat writes and
    raises an alert; TRV control is independent of the boiler thermostat.
    """
    room_temps: dict[str, float] = {}
    pushes: dict[str, float] = {}
    for room in inp.config.rooms:
        temp, external = select_temperature(
            room, inp.external_temps, inp.trv_temps, inp.now, inp.config.sensors, inp.learned_offsets
        )
        if temp is None:
            continue
        room_temps[room.name] = temp
        if external and not (room.floor_heating or room.open_radiators) and _needs_push(room.name, temp, inp):
            pushes[room.name] = temp
    boosted = boosted_rooms(inp.boosts, inp.now)
    paused = {k: v for k, v in window_pauses(inp).items() if k not in boosted}
    trv_setpoints: dict[str, float] = {}
    reasons: dict[str, Reason] = {}
    for room in inp.config.rooms:
        trv_setpoints[room.name], reasons[room.name] = _target(room, inp, boosted, paused)
    _floor_first(inp, trv_setpoints, reasons, room_temps)
    writes = trv_writes(inp, trv_setpoints)
    trv = check_trvs(inp, writes)
    # In Room terms: a corrected TRV's hand-set value minus the correction it was given.
    hand_set = {
        r: inp.trv_observed[r] - (writes[r] - trv_setpoints[r]) for r in trv.manual if r in inp.trv_observed
    }
    for room_name in hand_set:
        reasons[room_name] = "manual"
    calling = demand_rooms(inp.config, trv_setpoints, room_temps, hand_set, inp.coast, inp.settling)
    capping = _open_radiators_capping(inp, room_temps)
    if capping:
        calling = ()  # a room with open radiators is warm enough: stop heating the whole house
    demand = bool(calling) or manual_override_active(
        inp.manual_overrides, inp.now
    )
    ec_setpoint, reassert, ec_hold = boiler_setpoint(inp, demand)
    return Decision(
        trv_setpoints=trv_setpoints,
        boiler_setpoint=ec_setpoint,
        boiler_reassert=reassert,
        boiler_hold_until=ec_hold,
        trv_rewrite=trv.rewrite,
        trv_manual=trv.manual,
        trv_retries=trv.retries,
        reasons=reasons,
        alerts=(*compute_alerts(inp), *trv.alerts),
        room_temps=room_temps,
        external_temp_pushes=pushes,
        window_paused_until=paused,
        demand_rooms=calling,
        hand_set=hand_set,
        open_radiators_capping=capping,
        trv_writes=writes,
    )
