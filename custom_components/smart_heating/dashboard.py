"""Pure generator of the Lovelace dashboard (standard cards only, ADR-0005).

Entity ids are fixed by the entities themselves (see entity_id), so the
generated config can reference them. No Home Assistant imports.
"""

from __future__ import annotations

import json
import re
from typing import Any, Iterable, Mapping

from .const import DOMAIN
from .gather import battery_entity, heating_demand_entity, valve_position_entity

OPTIONS_LINK = f"/config/integrations/integration/{DOMAIN}"


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def entity_id(domain: str, room: str | None, key: str | None = None) -> str:
    """Object id: smart_heating_<room>[_<key>]. Room-less ids are system-wide."""
    parts = [DOMAIN]
    if room:
        parts.append(slug(room))
    if key:
        parts.append(key)
    return f"{domain}.{'_'.join(parts)}"


HELP_CONTENT = """\
## The overview
The top line says which rooms are heating and whether the boiler is on. Below it, every room
shows its temperature now, the temperature it is aiming for, and a short sentence about what
it is doing. Alerts only appear when something needs your attention.

## What the sentence in a room means
| You see | What it means |
|---|---|
| Warm until 17:00 | The room is in a scheduled warm period and is heated to its normal warm temperature. |
| Warm from 08:00 | The room is at its lower temperature now and warms up for its next scheduled period. |
| Kept at 16 degrees | The room stays at its lower temperature, nothing is scheduled. |
| Warming up, warm until 17:00 | The room started heating early so it is already warm when its schedule begins. |
| Boost until 14:00 | You pressed Boost. The room is heated to its warm temperature until then or until you cancel it. |
| Window seems open, heating paused until 14:20 | The room cooled down very fast, so a window is probably open. Heating is paused for a little while. |
| Nobody home, kept at 16 degrees | Nobody is home, so the room is kept a bit cooler. After a long absence it is only kept just above freezing. |
| Room's person is away, kept at 16 degrees | The person this room is for is away, so the schedule is skipped. The room warms up again when they are back or on their way. |
| Waiting for the floor heating to warm up first, kept at 12 degrees | A floor-heating room (slow to warm) is warming up for its schedule. Radiators in rooms that don't need warmth stay closed meanwhile, so the heat goes to the floor. |
| Set by hand to 22 degrees, until 17:00 | You turned the radiator valve yourself. It is left alone until the room's target changes, and the boiler is called if the room is colder than what you set. |
| Vacation until Mon 00:00, kept at 12 degrees | Vacation mode is on. The room is only kept just above freezing. The house warms up again before the day you come back. |

When two rules apply, the stronger one wins: Boost, then an open window, then Vacation, then
nobody home, then the schedule.

## The Heating page
- **Right now / Next change**: what the room is doing and when that changes next, with the temperature it changes to.
- **Pre-heat lead time**: how long before a schedule the room starts warming up. It starts as a fixed guess and improves as the system learns how fast each room heats.
- **Boost / Cancel boost**: warm this room now for a set time, or stop that early.
- **Radiator valve**: battery and valve details, useful when a room misbehaves.

## The Boiler page
- **Boiler is being called**: the boiler is told to heat. This only happens when at least one room that should be warm is clearly colder than it should be. Otherwise the boiler rests.
- **Rooms asking for heat**: which rooms caused the call.
- **Target we set on the EasyControl**: the temperature last sent to the thermostat that controls the boiler.
- **Last sent / Result of last send**: when we last told the EasyControl something, and whether it worked.
- **Paused after an error**: after an error the system waits a few minutes before trying again, so the Bosch cloud is not flooded.
- **Manual change on the EasyControl**: you changed the EasyControl yourself. That is respected for about two hours and the system does not overwrite it.
- **Manual room override**: for rooms where you turn the radiator on by hand. It tells the boiler to heat for a set time, since the system can't see that room. Use its cancel button to stop it early.

## Changed something by hand?
A radiator you turn by hand is left alone until that room's target next changes.
"""


STATUS = entity_id("sensor", None, "status")
ALERTS = entity_id("sensor", None, "active_alerts")

HEADER_CONTENT = (
    "## {{ states('sensor.smart_heating_status') }}\n"
    "{% set n = states('sensor.smart_heating_active_alerts') | int(0) %}"
    "{% if n > 0 %}**{{ n }} alert{{ 's' if n != 1 }}** need attention, see Alerts below."
    "{% else %}No alerts.{% endif %}"
)

ALERTS_CONTENT = (
    "{% for m in state_attr('sensor.smart_heating_active_alerts', 'messages') or [] %}"
    "- {{ m }}\n"
    "{% endfor %}"
)


def _normalize(room: str | Mapping[str, Any]) -> dict[str, Any]:
    return {"name": room} if isinstance(room, str) else dict(room)


def _heading(title: str, icon: str | None = None) -> dict[str, Any]:
    card: dict[str, Any] = {"type": "heading", "heading": title}
    if icon:
        card["icon"] = icon
    return card


def _section(*cards: dict[str, Any]) -> dict[str, Any]:
    return {"type": "grid", "cards": list(cards)}


def _room_section(room: Mapping[str, Any]) -> dict[str, Any]:
    name = room["name"]
    cards: list[dict[str, Any]] = [
        _heading(name, "mdi:radiator"),
        {
            "type": "entities",
            "entities": [
                {"entity": entity_id("climate", name)},
                {"entity": entity_id("sensor", name, "summary"), "name": "Right now"},
                {"entity": entity_id("sensor", name, "next_change"), "name": "Next change"},
                {"entity": entity_id("sensor", name, "lead_time"), "name": "Pre-heat lead time"},
                {"entity": entity_id("button", name, "boost"), "name": "Boost"},
                {"entity": entity_id("button", name, "cancel_boost"), "name": "Cancel boost"},
            ],
        },
        # Home Assistant draws a climate entity as current temperature, target and heating.
        {
            "type": "history-graph",
            "title": "Last 24 hours",
            "hours_to_show": 24,
            "entities": [{"entity": entity_id("climate", name)}],
        },
    ]
    trv = room.get("trv_entity")
    if trv:
        cards.append(
            {
                "type": "entities",
                "title": "Radiator valve",
                "entities": [
                    {"entity": battery_entity(trv), "name": "Battery"},
                    {"entity": valve_position_entity(trv), "name": "Valve opening"},
                    {"entity": heating_demand_entity(trv), "name": "Valve heating demand"},
                ],
            }
        )
    return _section(*cards)


def _rooms_table(rooms: list[dict[str, Any]]) -> str:
    """Markdown table, one row per room: temperature now, target, and the plain sentence."""

    def temp(entity: str, attr: str) -> str:
        value = f"state_attr('{entity}', '{attr}')"
        return f"{{{{ '%.1f' | format({value}) + '°' if {value} is number else '–' }}}}"

    lines = ["| Room | Now | Aiming for | |", "|---|---|---|---|"]
    for r in rooms:
        climate = entity_id("climate", r["name"])
        summary = entity_id("sensor", r["name"], "summary")
        lines.append(
            f"| **{r['name']}** | {temp(climate, 'current_temperature')} "
            f"| {temp(climate, 'temperature')} "
            f"| {{{{ states('{summary}') if has_value('{summary}') else '' }}}} |"
        )
    return "\n".join(lines)


def _overview_view(rooms: list[dict[str, Any]]) -> dict[str, Any]:
    now = _section(
        _heading("Right now", "mdi:home-thermometer"),
        {"type": "markdown", "content": HEADER_CONTENT},
        {"type": "markdown", "content": _rooms_table(rooms)},
    )
    alerts = _section(
        {
            "type": "conditional",
            "conditions": [{"entity": ALERTS, "state_not": "0"}],
            "card": {
                "type": "vertical-stack",
                "cards": [
                    _heading("Alerts", "mdi:alert"),
                    {"type": "markdown", "content": ALERTS_CONTENT},
                ],
            },
        }
    )
    controls = _section(
        _heading("Controls", "mdi:tune"),
        {
            "type": "entities",
            "entities": [
                {"entity": entity_id("switch", None, "vacation_mode")},
                {"entity": entity_id("number", None, "vacation_days")},
                {"entity": entity_id("button", None, "manual_room_override")},
                {"entity": entity_id("button", None, "cancel_manual_room_override")},
            ],
        },
        {
            "type": "markdown",
            "content": (
                "Edit schedules, comfort and setback per room under "
                f"[Smart Heating options]({OPTIONS_LINK}) (Configure, Edit a room)."
            ),
        },
    )
    return {
        "title": "Overview",
        "path": "overview",
        "icon": "mdi:home-thermometer",
        "type": "sections",
        "max_columns": 2,
        "sections": [now, alerts, controls],
    }


def _heating_view(rooms: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "title": "Heating",
        "path": "heating",
        "icon": "mdi:radiator",
        "type": "sections",
        "max_columns": 2,
        "sections": [_room_section(r) for r in rooms],
    }


def _boiler_view() -> dict[str, Any]:
    call = entity_id("binary_sensor", None, "boiler_call")
    target = entity_id("sensor", None, "boiler_target")
    details = _section(
        _heading("Boiler", "mdi:water-boiler"),
        {
            "type": "entities",
            "entities": [
                {"entity": call, "name": "Boiler is being called"},
                {"entity": entity_id("sensor", None, "boiler_demand_rooms"), "name": "Rooms asking for heat"},
                {"entity": target, "name": "Target we set on the EasyControl"},
                {"entity": entity_id("sensor", None, "boiler_last_write"), "name": "Last sent to the EasyControl"},
                {"entity": entity_id("sensor", None, "boiler_write_result"), "name": "Result of last send"},
                {"entity": entity_id("sensor", None, "boiler_backoff"), "name": "Paused after an error"},
                {"entity": entity_id("sensor", None, "boiler_manual_hold"), "name": "Manual change on the EasyControl"},
            ],
        },
        {
            "type": "entities",
            "title": "Manual room override",
            "entities": [
                {"entity": entity_id("button", None, "manual_room_override")},
                {"entity": entity_id("button", None, "cancel_manual_room_override")},
            ],
        },
    )
    history = _section(
        _heading("Last 24 hours", "mdi:chart-line"),
        {
            "type": "history-graph",
            "hours_to_show": 24,
            "entities": [{"entity": call}, {"entity": target}],
        },
    )
    return {
        "title": "Boiler",
        "path": "boiler",
        "icon": "mdi:water-boiler",
        "type": "sections",
        "max_columns": 2,
        "sections": [details, history],
    }


def build_dashboard(rooms: Iterable[str | Mapping[str, Any]]) -> dict[str, Any]:
    """Rooms are names or room dicts (name, optional trv_entity for the valve card)."""
    room_list = [_normalize(r) for r in rooms]
    return {
        "title": "Smart Heating",
        "views": [
            _overview_view(room_list),
            _heating_view(room_list),
            _boiler_view(),
            {
                "title": "Help",
                "path": "help",
                "icon": "mdi:help-circle-outline",
                "cards": [
                    {"type": "markdown", "title": "How to read this", "content": HELP_CONTENT}
                ],
            },
        ],
    }


def _scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return repr(value)
    return json.dumps(str(value))  # JSON strings are valid double-quoted YAML


def _emit(node: Any, indent: int, out: list[str]) -> None:
    pad = "  " * indent
    if isinstance(node, dict):
        for key, value in node.items():
            if isinstance(value, (dict, list)) and value:
                out.append(f"{pad}{key}:")
                _emit(value, indent + 1, out)
            else:
                out.append(f"{pad}{key}: {_empty_or_scalar(value)}")
    else:
        for item in node:
            if isinstance(item, dict) and item:
                lines: list[str] = []
                _emit(item, indent + 1, lines)
                out.append(f"{pad}- {lines[0].lstrip()}")
                out.extend(lines[1:])
            elif isinstance(item, list) and item:
                out.append(f"{pad}-")
                _emit(item, indent + 1, out)
            else:
                out.append(f"{pad}- {_empty_or_scalar(item)}")


def _empty_or_scalar(value: Any) -> str:
    if isinstance(value, dict):
        return "{}"
    if isinstance(value, list):
        return "[]"
    return _scalar(value)


def to_yaml(node: dict[str, Any]) -> str:
    out: list[str] = []
    _emit(node, 0, out)
    return "\n".join(out) + "\n"
