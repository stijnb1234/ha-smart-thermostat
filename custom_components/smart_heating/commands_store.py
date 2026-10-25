"""Thin HA Store wrapper persisting the engine's Commands and the start of an absence across
restarts and reloads (keyed by Room id)."""

from __future__ import annotations

from datetime import datetime

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .engine import Commands, commands_from_dict, commands_to_dict
from .engine.state import PER_ROOM_KEYS, away_since_from_dict
from .rooms import RoomKeys

STORAGE_KEY = "smart_heating.commands"
SAVE_DELAY_SECONDS = 5


class CommandsStore:
    def __init__(self, hass: HomeAssistant, keys: RoomKeys) -> None:
        self._store: Store = Store(hass, 1, STORAGE_KEY)
        self._keys = keys
        self._saved: dict | None = None

    async def async_load(self, rooms) -> tuple[Commands, datetime | None]:
        data = self._keys.sections_to_names(await self._store.async_load(), PER_ROOM_KEYS)
        return commands_from_dict(data, rooms), away_since_from_dict(data)

    def save_if_changed(self, commands: Commands, away_since: datetime | None) -> None:
        data = self._keys.sections_to_ids(commands_to_dict(commands, away_since), PER_ROOM_KEYS)
        if data != self._saved:
            self._saved = data
            self._store.async_delay_save(lambda: data, SAVE_DELAY_SECONDS)
