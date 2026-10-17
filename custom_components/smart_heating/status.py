"""Pure plain-language status of the system: boiler, heating rooms, alerts.

Feeds the status/boiler/alert sensors and so the dashboard. Times passed in
are expected to be in the user's local timezone. No Home Assistant imports.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Mapping

from .engine import Alert, Decision, EngineConfig, EngineInput
from .engine.boiler import backoff_delay
from .engine.overrides import manual_override_active

MANUAL_OVERRIDE_LABEL = "Manual room override"


@dataclass(frozen=True)
class BoilerStatus:
    call_active: bool
    demand_rooms: tuple[str, ...]
    manual_override: bool
    held_setpoint: float | None
    last_write_at: datetime | None
    last_write_result: str  # ok / rate_limited / error / none
    backoff_until: datetime | None
    hold_until: datetime | None = None  # a manual EasyControl change is being respected until


def boiler_status(inp: EngineInput, decision: Decision) -> BoilerStatus:
    # The adapter writes the decision's setpoint this cycle, so that is what we hold.
    held = decision.easycontrol_setpoint
    if held is None:
        held = inp.last_commands.easycontrol_setpoint
    cfg = inp.config
    call = held is not None and cfg.easycontrol_high != cfg.easycontrol_low and held == cfg.easycontrol_high
    result = inp.last_write
    backoff_until = None
    if result is not None and result.status != "ok":
        until = result.at + backoff_delay(cfg, result)
        if until > inp.now:
            backoff_until = until
    hold_until = decision.easycontrol_hold_until
    if hold_until is not None and hold_until <= inp.now:
        hold_until = None
    return BoilerStatus(
        call_active=call,
        demand_rooms=decision.demand_rooms,
        manual_override=manual_override_active(inp.manual_overrides, inp.now),
        held_setpoint=held,
        last_write_at=result.at if result else None,
        last_write_result=result.status if result else "none",
        backoff_until=backoff_until,
        hold_until=hold_until,
    )


def demand_text(status: BoilerStatus) -> str:
    names = [*status.demand_rooms, *([MANUAL_OVERRIDE_LABEL] if status.manual_override else [])]
    return ", ".join(names) if names else "None"


def _clock(at: datetime) -> str:
    return at.strftime("%H:%M")


def backoff_text(until: datetime | None, now: datetime) -> str:
    if until is None:
        return "No"
    stamp = _clock(until) if until.date() == now.date() else until.strftime("%a %H:%M")
    return f"Waiting until {stamp}"


def hold_text(until: datetime | None, now: datetime) -> str:
    if until is None:
        return "No"
    stamp = _clock(until) if until.date() == now.date() else until.strftime("%a %H:%M")
    return f"Respecting a manual change until {stamp}"


def heating_rooms(
    config: EngineConfig,
    trv_setpoints: Mapping[str, float],
    room_temps: Mapping[str, float],
) -> tuple[str, ...]:
    """Rooms clearly colder than their target (so their valve is open and heating)."""
    return tuple(
        room.name
        for room in config.rooms
        if room.name in room_temps
        and room.name in trv_setpoints
        and room_temps[room.name] < trv_setpoints[room.name] - config.demand_hysteresis
    )


def status_text(
    heating: tuple[str, ...], boiler_on: bool, vacation: bool, away: bool
) -> str:
    head = f"Heating: {', '.join(heating)}." if heating else "Nothing is heating."
    parts = [head, "Boiler on." if boiler_on else "Boiler off."]
    if vacation:
        parts.append("Vacation mode is on.")
    elif away:
        parts.append("Nobody is home.")
    return " ".join(parts)


def alert_sentence(alert: Alert) -> str:
    room = alert.room or "a room"
    sentences = {
        "bosch_outage": (
            "The Bosch cloud cannot be reached, so the boiler cannot be called reliably. "
            "The radiator valves keep following the schedule."
        ),
        "trv_offline": f"The radiator valve in {room} is not responding.",
        "low_battery": f"The battery of the radiator valve in {room} is low. Replace it soon.",
        "sensor_stale": f"The temperature sensor in {room} stopped reporting.",
        "target_not_reached": f"{room} has been too cold for a long time and is not reaching its target.",
    }
    return sentences.get(alert.code) or alert.message or alert.code
