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
Each room has a target temperature. **Why** tells you the reason for it right now.
The rules at the top win over the ones below.

| Why | What it means |
|---|---|
| boost | You pressed Boost. The room is heated to its normal warm temperature until the boost runs out or you cancel it. |
| window | The room cooled down very fast, so a window is probably open. Heating is paused for a little while. |
| vacation | Vacation mode is on. The room is only kept just above freezing. |
| away | Nobody is home. The room is kept a bit cooler than normal. After a long absence it is only kept just above freezing. |
| pre_heat | The room is heating up early so it is already warm when its schedule starts. |
| schedule | The room is in a scheduled warm period, so it is heated to its normal warm temperature. |
| setback | Nobody needs this room warm now, so it stays at its lower temperature. |

**Next change** shows when the target changes next, and to what temperature.
**Pre-heat lead time** is how long before a schedule the room starts warming up. It starts as a fixed guess and improves as the system learns how fast each room heats.

**When does the boiler turn on?** Only when at least one room that should be warm is clearly colder than it should be. When no room needs heat, the boiler is allowed to rest.

**Manual room override** is for rooms where you turn the radiator on by hand. It tells the boiler to heat for a set time, since the system can't see that room. Use its cancel button to stop it early.
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
                "title": "Radiator valve (technical)",
                "entities": [
                    {"entity": battery_entity(trv), "name": "Battery"},
                    {"entity": valve_position_entity(trv), "name": "Valve opening"},
                    {"entity": heating_demand_entity(trv), "name": "Valve heating demand"},
                ],
            }
        )
    return _section(*cards)


def _overview_view(rooms: list[dict[str, Any]]) -> dict[str, Any]:
    now = _section(
        _heading("Right now", "mdi:home-thermometer"),
        {"type": "markdown", "content": HEADER_CONTENT},
        {
            "type": "grid",
            "columns": 2,
            "square": False,
            "cards": [
                {"type": "tile", "entity": entity_id("climate", r["name"]), "name": r["name"]}
                for r in rooms
            ],
        },
    )
    boiler = _section(
        _heading("Boiler", "mdi:water-boiler"),
        {
            "type": "entities",
            "entities": [
                {"entity": entity_id("binary_sensor", None, "boiler_call"), "name": "Boiler is being called"},
                {"entity": entity_id("sensor", None, "boiler_demand_rooms"), "name": "Rooms asking for heat"},
                {"entity": entity_id("sensor", None, "boiler_target"), "name": "Target we set on the EasyControl"},
                {"entity": entity_id("sensor", None, "boiler_last_write"), "name": "Last sent to the EasyControl"},
                {"entity": entity_id("sensor", None, "boiler_write_result"), "name": "Result of last send"},
                {"entity": entity_id("sensor", None, "boiler_backoff"), "name": "Paused after an error"},
                # TODO: show manual hold here once the manual-hold feature lands.
            ],
        },
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
        "sections": [now, alerts, boiler, controls],
    }


def build_dashboard(rooms: Iterable[str | Mapping[str, Any]]) -> dict[str, Any]:
    """Rooms are names or room dicts (name, optional trv_entity for the technical card)."""
    room_list = [_normalize(r) for r in rooms]
    return {
        "title": "Smart Heating",
        "views": [
            _overview_view(room_list),
            {
                "title": "Rooms",
                "path": "rooms",
                "icon": "mdi:radiator",
                "type": "sections",
                "max_columns": 2,
                "sections": [_room_section(r) for r in room_list],
            },
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
