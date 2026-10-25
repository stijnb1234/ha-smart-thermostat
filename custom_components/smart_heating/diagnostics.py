"""Diagnostics download (Settings > Devices & services > Smart Heating > Download diagnostics).

Everything needed to understand a report from another home: configuration, what each TRV
offers, the last decision and what has been learned. Person and calendar entity ids are
redacted; GPS positions are never included.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_ARRIVAL_ENTITIES, CONF_PERSONS, CONF_VACATION_CALENDAR, DOMAIN
from .engine import commands_to_dict

TO_REDACT = {CONF_PERSONS, CONF_ARRIVAL_ENTITIES, CONF_VACATION_CALENDAR, "presence_entities", "arrival_entities"}


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_jsonable(v) for v in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if hasattr(value, "total_seconds"):
        return value.total_seconds()
    return value


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    shared = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    coordinator = shared.get("coordinator")
    result: dict[str, Any] = {
        "version": entry.version,
        "options": async_redact_data(dict(entry.options), TO_REDACT),
    }
    if coordinator is None:
        return result
    cycle = coordinator.data
    controller = coordinator.controller
    result["trv_devices"] = {room: asdict(d) for room, d in coordinator.trv_devices.items()}
    result["commands"] = commands_to_dict(controller.commands, controller.away_since)
    result["insights"] = controller.insights.to_dict()
    result["lead_time_samples"] = coordinator.learner.to_dict()
    vacation = shared["vacation"].planner
    result["vacation"] = {
        "manual": vacation.manual.to_dict() if vacation.manual else None,
        "calendar": [p.to_dict() for p in vacation.calendar],
    }
    if cycle is not None:
        d = cycle.decision
        result["last_cycle"] = _jsonable(
            {
                "now": cycle.inp.now,
                "anyone_home": cycle.inp.anyone_home,
                "away_since": cycle.inp.away_since,
                "vacation_until": cycle.inp.vacation_until,
                "absent_rooms": cycle.inp.absent_rooms,
                "cooling_rooms": cycle.inp.cooling_rooms,
                "room_temps": d.room_temps,
                "targets": d.trv_setpoints,
                "reasons": d.reasons,
                "lead_times": cycle.lead_times,
                "demand_rooms": d.demand_rooms,
                "boiler_setpoint": d.boiler_setpoint,
                "boiler_hold_until": d.boiler_hold_until,
                "window_paused_until": d.window_paused_until,
                "alerts": [{"code": a.code, "room": a.room} for a in d.alerts],
            }
        )
    return result
