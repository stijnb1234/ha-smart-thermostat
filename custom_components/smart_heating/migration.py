"""Pure config entry migrations. No Home Assistant imports.

Version 2: thermostat-specific option names become generic boiler options, and every
Room gets a stable id; entity unique ids move from the Room name to that id.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .const import CONF_ROOMS
from .rooms import ensure_room_ids

CONFIG_VERSION = 2

OPTION_RENAMES = {
    "easycontrol_entity": "boiler_entity",
    "easycontrol_low": "boiler_low",
    "easycontrol_high": "boiler_high",
    "easycontrol_settle_minutes": "boiler_settle_minutes",
    "easycontrol_manual_hold_minutes": "boiler_manual_hold_minutes",
}


def migrate_options(options: Mapping[str, Any], version: int) -> dict[str, Any]:
    """Options of a config entry at `version`, brought to CONFIG_VERSION."""
    result = dict(options)
    if version < 2:
        result = {OPTION_RENAMES.get(k, k): v for k, v in result.items()}
        result[CONF_ROOMS] = ensure_room_ids(result.get(CONF_ROOMS, []))
    return result


def migrate_unique_id(unique_id: str, entry_id: str, rooms: Sequence[Mapping[str, Any]]) -> str | None:
    """New unique id for an entity whose id ended in a Room name, or None to leave it alone.

    Longer names are tried first so 'Guest_Bed' wins over 'Bed'."""
    if not unique_id.startswith(f"{entry_id}_"):
        return None
    for room in sorted(rooms, key=lambda r: len(r["name"]), reverse=True):
        suffix = f"_{room['name']}"
        if unique_id.endswith(suffix):
            new = unique_id[: -len(suffix)] + f"_{room['id']}"
            return None if new == unique_id else new
    return None
