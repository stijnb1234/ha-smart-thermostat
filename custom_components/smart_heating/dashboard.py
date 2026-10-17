"""Pure generator of the Lovelace dashboard (standard cards only, ADR-0005).

Entity ids are fixed by the entities themselves (see entity_id), so the
generated config can reference them. No Home Assistant imports.
"""

from __future__ import annotations

import json
import re
from typing import Any, Iterable

from .const import DOMAIN

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
**Why** shows which rule sets a room's current target (strongest first):

| Why | Meaning |
|---|---|
| boost | You pressed Boost: comfort until it expires or you cancel it. |
| window | A fast temperature drop looks like an open window; heating is paused for 15-30 min. |
| vacation | Vacation mode is on: frost-hold (12 °C). |
| away | Nobody is home: setback, or frost-hold after a long absence. |
| pre_heat | Heating early so the room is warm when its schedule starts. |
| schedule | Inside a comfort window: comfort temperature. |
| setback | Nothing asks for heat: the lower setback temperature. |

**Next change** is when the target changes next and what it becomes.
**Pre-heat lead time** is how long before a schedule the room starts heating (learned over time).

The boiler fires (EasyControl setpoint raised) only while a room at comfort is colder than its target.
**Manual room override** fires the boiler for rooms with dumb radiator valves; cancel it with its cancel button.
"""


def _room_card(room: str) -> dict[str, Any]:
    return {
        "type": "entities",
        "title": room,
        "entities": [
            {"entity": entity_id("climate", room)},
            {"entity": entity_id("sensor", room, "reason"), "name": "Why"},
            {"entity": entity_id("sensor", room, "next_change"), "name": "Next change"},
            {"entity": entity_id("sensor", room, "lead_time"), "name": "Pre-heat lead time"},
            {"entity": entity_id("button", room, "boost"), "name": "Boost"},
            {"entity": entity_id("button", room, "cancel_boost"), "name": "Cancel boost"},
        ],
    }


def build_dashboard(rooms: Iterable[str]) -> dict[str, Any]:
    rooms = list(rooms)
    controls = {
        "type": "entities",
        "title": "Controls",
        "entities": [
            {"entity": entity_id("switch", None, "vacation_mode")},
            {"entity": entity_id("number", None, "vacation_days")},
            {"entity": entity_id("button", None, "manual_room_override")},
            {"entity": entity_id("button", None, "cancel_manual_room_override")},
        ],
    }
    schedules = {
        "type": "markdown",
        "title": "Schedules",
        "content": (
            "Edit schedules, comfort and setback per room under "
            f"[Smart Heating options]({OPTIONS_LINK}) (Configure, Edit a room)."
        ),
    }
    help_card = {"type": "markdown", "title": "How to read this", "content": HELP_CONTENT}
    return {
        "title": "Smart Heating",
        "views": [
            {
                "title": "Heating",
                "path": "heating",
                "icon": "mdi:radiator",
                "cards": [*map(_room_card, rooms), controls, schedules, help_card],
            }
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
