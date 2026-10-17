"""Thin HA glue: Boost and cancel-Boost buttons per Room, and Manual-room override start/cancel buttons.

Pressing a button records a start time and the configured duration in the entry's shared
`boosts` / `manual_overrides` dicts; the coordinator passes those to the engine,
which decides when they expire.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.button import ButtonEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .dashboard import entity_id
from .engine import Boost, ManualRoomOverride

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

MANUAL_OVERRIDE_KEY = "manual_room"


class BoostButton(ButtonEntity):
    _attr_has_entity_name = True

    def __init__(self, entry_id: str, room: str, state: dict) -> None:
        self._room, self._state = room, state
        self._attr_name = f"{room} boost"
        self._attr_unique_id = f"{entry_id}_boost_{room}"
        self.entity_id = entity_id("button", room, "boost")

    async def async_press(self) -> None:
        self._state["boosts"][self._room] = Boost(dt_util.utcnow(), self._state["boost_duration"])
        await _refresh(self._state)


class CancelBoostButton(ButtonEntity):
    _attr_has_entity_name = True

    def __init__(self, entry_id: str, room: str, state: dict) -> None:
        self._room, self._state = room, state
        self._attr_name = f"{room} cancel boost"
        self._attr_unique_id = f"{entry_id}_cancel_boost_{room}"
        self.entity_id = entity_id("button", room, "cancel_boost")

    async def async_press(self) -> None:
        self._state["boosts"].pop(self._room, None)
        await _refresh(self._state)


class CancelManualRoomOverrideButton(ButtonEntity):
    _attr_has_entity_name = True
    _attr_name = "Cancel manual room override"
    entity_id = "button.smart_heating_cancel_manual_room_override"

    def __init__(self, entry_id: str, state: dict) -> None:
        self._state = state
        self._attr_unique_id = f"{entry_id}_cancel_manual_room_override"

    async def async_press(self) -> None:
        self._state["manual_overrides"].pop(MANUAL_OVERRIDE_KEY, None)
        await _refresh(self._state)


class ManualRoomOverrideButton(ButtonEntity):
    _attr_has_entity_name = True
    _attr_name = "Manual room override"
    entity_id = "button.smart_heating_manual_room_override"

    def __init__(self, entry_id: str, state: dict) -> None:
        self._state = state
        self._attr_unique_id = f"{entry_id}_manual_room_override"

    async def async_press(self) -> None:
        self._state["manual_overrides"][MANUAL_OVERRIDE_KEY] = ManualRoomOverride(
            dt_util.utcnow(), self._state["manual_override_duration"]
        )
        await _refresh(self._state)


async def _refresh(state: dict) -> None:
    """Persist the request (survives reloads), then re-run the control cycle now."""
    await state["override_store"].async_save(state["boosts"], state["manual_overrides"])
    if (coordinator := state.get("coordinator")) is not None:
        await coordinator.async_request_refresh()


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    state = hass.data[DOMAIN][entry.entry_id]
    entities = [BoostButton(entry.entry_id, r.name, state) for r in state["rooms"]]
    entities += [CancelBoostButton(entry.entry_id, r.name, state) for r in state["rooms"]]
    entities.append(ManualRoomOverrideButton(entry.entry_id, state))
    entities.append(CancelManualRoomOverrideButton(entry.entry_id, state))
    async_add_entities(entities)
