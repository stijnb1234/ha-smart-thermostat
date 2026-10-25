"""Pure plain-language status of the system: boiler, heating rooms, alerts.

Feeds the status/boiler/alert sensors and so the dashboard. Times passed in
are expected to be in the user's local timezone. No Home Assistant imports.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime

from .engine import Alert, Decision, EngineConfig, EngineInput
from .engine.boiler import backoff_delay
from .engine.overrides import manual_override_active
from .i18n import DEFAULT_LANGUAGE, tr, weekday


@dataclass(frozen=True)
class BoilerStatus:
    call_active: bool
    demand_rooms: tuple[str, ...]
    manual_override: bool
    held_setpoint: float | None
    last_write_at: datetime | None
    last_write_result: str  # ok / rate_limited / error / none
    backoff_until: datetime | None
    hold_until: datetime | None = None  # a manual change on the boiler thermostat is being respected until


def boiler_status(inp: EngineInput, decision: Decision) -> BoilerStatus:
    # The adapter writes the decision's setpoint this cycle, so that is what we hold.
    held = decision.boiler_setpoint
    if held is None:
        held = inp.last_commands.boiler_setpoint
    cfg = inp.config
    call = held is not None and cfg.boiler_high != cfg.boiler_low and held == cfg.boiler_high
    result = inp.last_write
    backoff_until = None
    if result is not None and result.status != "ok":
        until = result.at + backoff_delay(cfg, result)
        if until > inp.now:
            backoff_until = until
    hold_until = decision.boiler_hold_until
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


def demand_text(status: BoilerStatus, lang: str = DEFAULT_LANGUAGE) -> str:
    names = [*status.demand_rooms, *([tr(lang, "demand.manual_override")] if status.manual_override else [])]
    return ", ".join(names) if names else tr(lang, "demand.none")


def _clock(at: datetime) -> str:
    return at.strftime("%H:%M")


def _stamp(at: datetime, now: datetime, lang: str) -> str:
    return _clock(at) if at.date() == now.date() else f"{weekday(lang, at.weekday())} {_clock(at)}"


def backoff_text(until: datetime | None, now: datetime, lang: str = DEFAULT_LANGUAGE) -> str:
    if until is None:
        return tr(lang, "backoff.no")
    return tr(lang, "backoff.waiting", at=_stamp(until, now, lang))


def hold_text(until: datetime | None, now: datetime, lang: str = DEFAULT_LANGUAGE) -> str:
    if until is None:
        return tr(lang, "hold.no")
    return tr(lang, "hold.respecting", at=_stamp(until, now, lang))


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
    heating: tuple[str, ...],
    boiler_on: bool,
    vacation: bool,
    away: bool,
    lang: str = DEFAULT_LANGUAGE,
) -> str:
    head = tr(lang, "status.heating", rooms=", ".join(heating)) if heating else tr(lang, "status.nothing")
    parts = [head, tr(lang, "status.boiler_on" if boiler_on else "status.boiler_off")]
    if vacation:
        parts.append(tr(lang, "status.vacation"))
    elif away:
        parts.append(tr(lang, "status.away"))
    return " ".join(parts)


def alert_sentence(alert: Alert, lang: str = DEFAULT_LANGUAGE) -> str:
    room = alert.room or tr(lang, "alert.a_room")
    key = f"alert.{alert.code}"
    if key in _ALERT_KEYS:
        return tr(lang, key, room=room)
    return alert.message or alert.code


_ALERT_KEYS = {
    f"alert.{c}"
    for c in (
        "boiler_outage", "trv_offline", "trv_off", "trv_write_failed",
        "low_battery", "sensor_stale", "target_not_reached", "not_warming",
    )
}
