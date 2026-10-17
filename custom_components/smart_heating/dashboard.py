"""Pure generator of the Lovelace dashboard (standard cards only, ADR-0005).

Entity ids are fixed by the entities themselves (see entity_id), so the
generated config can reference them. No Home Assistant imports.
"""

from __future__ import annotations

import json
import re
from typing import Any, Iterable, Mapping

from .const import DOMAIN
from .i18n import DEFAULT_LANGUAGE, help_cards, tr
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


STATUS = entity_id("sensor", None, "status")
ALERTS = entity_id("sensor", None, "active_alerts")

ALERTS_CONTENT = (
    "{% for m in state_attr('sensor.smart_heating_active_alerts', 'messages') or [] %}"
    "- {{ m }}\n"
    "{% endfor %}"
)


def _header_content(lang: str) -> str:
    return (
        "## {{ states('sensor.smart_heating_status') }}\n"
        "{% set n = states('sensor.smart_heating_active_alerts') | int(0) %}"
        + tr(lang, "dash.header_alerts")
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


def _room_section(room: Mapping[str, Any], lang: str) -> dict[str, Any]:
    name = room["name"]
    cards: list[dict[str, Any]] = [
        _heading(name, "mdi:radiator"),
        {
            "type": "entities",
            "entities": [
                {"entity": entity_id("climate", name)},
                {"entity": entity_id("sensor", name, "summary"), "name": tr(lang, "dash.right_now")},
                {"entity": entity_id("sensor", name, "next_change"), "name": tr(lang, "dash.next_change")},
                {"entity": entity_id("sensor", name, "lead_time"), "name": tr(lang, "dash.lead_time")},
                {"entity": entity_id("button", name, "boost"), "name": tr(lang, "dash.boost")},
                {"entity": entity_id("button", name, "cancel_boost"), "name": tr(lang, "dash.cancel_boost")},
            ],
        },
        # Home Assistant draws a climate entity as current temperature, target and heating.
        {
            "type": "history-graph",
            "title": tr(lang, "dash.last_24h"),
            "hours_to_show": 24,
            "entities": [{"entity": entity_id("climate", name)}],
        },
    ]
    trv = room.get("trv_entity")
    if trv:
        cards.append(
            {
                "type": "entities",
                "title": tr(lang, "dash.radiator_valve"),
                "entities": [
                    {"entity": battery_entity(trv), "name": tr(lang, "dash.battery")},
                    {"entity": valve_position_entity(trv), "name": tr(lang, "dash.valve_opening")},
                    {"entity": heating_demand_entity(trv), "name": tr(lang, "dash.valve_demand")},
                ],
            }
        )
    return _section(*cards)


def _rooms_table(rooms: list[dict[str, Any]], lang: str) -> str:
    """Markdown table, one row per room: temperature now, target, and the plain sentence."""

    def temp(entity: str, attr: str) -> str:
        value = f"state_attr('{entity}', '{attr}')"
        return f"{{{{ '%.1f' | format({value}) + '°' if {value} is number else '–' }}}}"

    t = lambda key: tr(lang, key)  # noqa: E731
    lines = [
        f"| {t('dash.table.room')} | {t('dash.table.now')} | {t('dash.table.aiming')} | {t('dash.table.what')} |",
        "|---|---|---|---|",
    ]
    for r in rooms:
        climate = entity_id("climate", r["name"])
        summary = entity_id("sensor", r["name"], "summary")
        lines.append(
            f"| **{r['name']}** | {temp(climate, 'current_temperature')} "
            f"| {temp(climate, 'temperature')} "
            f"| {{{{ states('{summary}') if has_value('{summary}') else '' }}}} |"
        )
    return "\n".join(lines)


def _overview_view(rooms: list[dict[str, Any]], lang: str) -> dict[str, Any]:
    """For everyone at home: what is happening, plus every control."""
    now = _section(
        _heading(tr(lang, "dash.right_now"), "mdi:home-thermometer"),
        {"type": "markdown", "content": _header_content(lang)},
        {"type": "markdown", "content": _rooms_table(rooms, lang)},
    )
    alerts = _section(
        {
            "type": "conditional",
            "conditions": [{"entity": ALERTS, "state_not": "0"}],
            "card": {
                "type": "vertical-stack",
                "cards": [
                    _heading(tr(lang, "dash.alerts"), "mdi:alert"),
                    {"type": "markdown", "content": ALERTS_CONTENT},
                ],
            },
        }
    )
    boosts = []
    for r in rooms:
        boosts += [
            {
                "entity": entity_id("button", r["name"], "boost"),
                "name": f"{r['name']}: {tr(lang, 'dash.boost')}",
            },
            {
                "entity": entity_id("button", r["name"], "cancel_boost"),
                "name": f"{r['name']}: {tr(lang, 'dash.cancel_boost')}",
            },
        ]
    controls = _section(
        _heading(tr(lang, "dash.controls"), "mdi:tune"),
        {
            "type": "entities",
            "entities": [
                {"entity": entity_id("switch", None, "vacation_mode")},
                {"entity": entity_id("number", None, "vacation_days")},
                {"entity": entity_id("button", None, "manual_room_override")},
                {"entity": entity_id("button", None, "cancel_manual_room_override")},
            ],
        },
        {"type": "entities", "title": tr(lang, "dash.boost"), "entities": boosts},
        {"type": "markdown", "content": tr(lang, "dash.options_hint", link=OPTIONS_LINK)},
    )
    return {
        "title": tr(lang, "dash.view.overview"),
        "path": "overview",
        "icon": "mdi:home-thermometer",
        "type": "sections",
        "max_columns": 2,
        "sections": [now, alerts, controls],
    }


def _heating_view(rooms: list[dict[str, Any]], lang: str) -> dict[str, Any]:
    return {
        "title": tr(lang, "dash.view.heating"),
        "path": "heating",
        "icon": "mdi:radiator",
        "type": "sections",
        "max_columns": 2,
        "sections": [_room_section(r, lang) for r in rooms],
    }


def _boiler_view(lang: str) -> dict[str, Any]:
    call = entity_id("binary_sensor", None, "boiler_call")
    target = entity_id("sensor", None, "boiler_target")
    t = lambda key: tr(lang, key)  # noqa: E731
    details = _section(
        _heading(t("dash.boiler"), "mdi:water-boiler"),
        {
            "type": "entities",
            "entities": [
                {"entity": call, "name": t("dash.boiler_called")},
                {"entity": entity_id("sensor", None, "boiler_demand_rooms"), "name": t("dash.demand_rooms")},
                {"entity": target, "name": t("dash.target")},
                {"entity": entity_id("sensor", None, "boiler_last_write"), "name": t("dash.last_sent")},
                {"entity": entity_id("sensor", None, "boiler_write_result"), "name": t("dash.write_result")},
                {"entity": entity_id("sensor", None, "boiler_backoff"), "name": t("dash.paused")},
                {"entity": entity_id("sensor", None, "boiler_manual_hold"), "name": t("dash.manual_hold")},
            ],
        },
        {
            "type": "entities",
            "title": t("dash.manual_override"),
            "entities": [
                {"entity": entity_id("button", None, "manual_room_override")},
                {"entity": entity_id("button", None, "cancel_manual_room_override")},
            ],
        },
    )
    history = _section(
        _heading(t("dash.last_24h"), "mdi:chart-line"),
        {
            "type": "history-graph",
            "hours_to_show": 24,
            "entities": [{"entity": call}, {"entity": target}],
        },
    )
    return {
        "title": t("dash.view.boiler"),
        "path": "boiler",
        "icon": "mdi:water-boiler",
        "type": "sections",
        "max_columns": 2,
        "sections": [details, history],
    }


def _help_view(lang: str) -> dict[str, Any]:
    """Short cards, one per topic, so wide screens fill several columns."""
    return {
        "title": tr(lang, "dash.view.help"),
        "path": "help",
        "icon": "mdi:help-circle-outline",
        "type": "sections",
        "max_columns": 3,
        "sections": [
            _section({"type": "markdown", "title": title, "content": body})
            for title, body in help_cards(lang)
        ],
    }


def build_dashboard(
    rooms: Iterable[str | Mapping[str, Any]], lang: str = DEFAULT_LANGUAGE
) -> dict[str, Any]:
    """Rooms are names or room dicts (name, optional trv_entity for the valve card)."""
    room_list = [_normalize(r) for r in rooms]
    return {
        "title": tr(lang, "dash.title"),
        "views": [
            _overview_view(room_list, lang),
            _heating_view(room_list, lang),
            _boiler_view(lang),
            _help_view(lang),
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
