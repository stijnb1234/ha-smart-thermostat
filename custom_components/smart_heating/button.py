"""Thin HA glue: a Boost button per Room and a Manual-room override button.

Pressing a button records a start time and duration in the entry's shared
`boosts` / `manual_overrides` dicts; the coordinator passes those to the engine,
which decides when they expire.
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from homeassistant.components.button import ButtonEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .engine import Boost, ManualRoomOverride

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

BOOST_DURATION = timedelta(minutes=60)
MANUAL_OVERRIDE_DURATION = timedelta(hours=2)
MANUAL_OVERRIDE_KEY = "manual_room"


class BoostButton(ButtonEntity):
    _attr_has_entity_name = True

    def __init__(self, entry_id: str, room: str, state: dict) -> None:
        self._room, self._state = room, state
        self._attr_name = f"{room} boost"
        self._attr_unique_id = f"{entry_id}_boost_{room}"

    async def async_press(self) -> None:
        self._state["boosts"][self._room] = Boost(dt_util.utcnow(), BOOST_DURATION)


class ManualRoomOverrideButton(ButtonEntity):
    _attr_has_entity_name = True
    _attr_name = "Manual room override"

    def __init__(self, entry_id: str, state: dict) -> None:
        self._state = state
        self._attr_unique_id = f"{entry_id}_manual_room_override"

    async def async_press(self) -> None:
        self._state["manual_overrides"][MANUAL_OVERRIDE_KEY] = ManualRoomOverride(
            dt_util.utcnow(), MANUAL_OVERRIDE_DURATION
        )


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    state = hass.data[DOMAIN][entry.entry_id]
    entities = [BoostButton(entry.entry_id, r.name, state) for r in state["rooms"]]
    entities.append(ManualRoomOverrideButton(entry.entry_id, state))
    async_add_entities(entities)
