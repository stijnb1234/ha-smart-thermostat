"""Thin HA Store wrapper persisting the engine's Commands across restarts and reloads."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .engine import Commands, commands_from_dict, commands_to_dict

STORAGE_KEY = "smart_heating.commands"
SAVE_DELAY_SECONDS = 5


class CommandsStore:
    def __init__(self, hass: HomeAssistant) -> None:
        self._store: Store = Store(hass, 1, STORAGE_KEY)
        self._saved: dict | None = None

    async def async_load(self, rooms) -> Commands:
        data = await self._store.async_load()
        self._saved = data
        return commands_from_dict(data, rooms)

    def save_if_changed(self, commands: Commands) -> None:
        data = commands_to_dict(commands)
        if data != self._saved:
            self._saved = data
            self._store.async_delay_save(lambda: data, SAVE_DELAY_SECONDS)
