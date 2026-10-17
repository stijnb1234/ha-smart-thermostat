"""Thin HA Store wrapper persisting Boosts and the Manual-room override across reloads/restarts.

The (de)serialisation is pure and tested in engine/overrides.py.
"""

from __future__ import annotations

from datetime import datetime
from typing import Mapping

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .engine import (
    Boost,
    ManualRoomOverride,
    timed_requests_from_dict,
    timed_requests_to_dict,
)

STORAGE_KEY = "smart_heating.timed_requests"
STORAGE_VERSION = 1


class OverrideStore:
    def __init__(self, hass: HomeAssistant) -> None:
        self._store: Store = Store(hass, STORAGE_VERSION, STORAGE_KEY)

    async def async_load(
        self, now: datetime
    ) -> tuple[dict[str, Boost], dict[str, ManualRoomOverride]]:
        return timed_requests_from_dict(await self._store.async_load(), now)

    async def async_save(
        self, boosts: Mapping[str, Boost], overrides: Mapping[str, ManualRoomOverride]
    ) -> None:
        await self._store.async_save(timed_requests_to_dict(boosts, overrides))
