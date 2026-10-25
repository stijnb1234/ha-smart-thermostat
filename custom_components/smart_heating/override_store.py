"""Thin HA Store wrapper persisting Boosts and the Manual-room override across reloads/restarts.

The (de)serialisation is pure and tested in engine/overrides.py.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .engine import (
    Boost,
    ManualRoomOverride,
    timed_requests_from_dict,
    timed_requests_to_dict,
)
from .rooms import RoomKeys

STORAGE_KEY = "smart_heating.timed_requests"
STORAGE_VERSION = 1
SECTIONS = ("boosts",)  # keyed by Room id; the Manual-room override is not per Room


class OverrideStore:
    def __init__(self, hass: HomeAssistant, keys: RoomKeys) -> None:
        self._store: Store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._keys = keys

    async def async_load(
        self, now: datetime
    ) -> tuple[dict[str, Boost], dict[str, ManualRoomOverride]]:
        data = self._keys.sections_to_names(await self._store.async_load(), SECTIONS)
        return timed_requests_from_dict(data, now)

    async def async_save(
        self, boosts: Mapping[str, Boost], overrides: Mapping[str, ManualRoomOverride]
    ) -> None:
        await self._store.async_save(self._keys.sections_to_ids(timed_requests_to_dict(boosts, overrides), SECTIONS))
