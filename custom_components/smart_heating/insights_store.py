"""Thin Home Assistant Store wrapper persisting the learned Room insights (keyed by Room id)."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .engine.insights import SCHEMA_VERSION, RoomInsights
from .rooms import RoomKeys

STORAGE_KEY = "smart_heating.room_insights"
SECTIONS = ("drops", "coasts", "offsets", "events")


class InsightsStore:
    def __init__(self, hass: HomeAssistant, keys: RoomKeys) -> None:
        self._store: Store = Store(hass, SCHEMA_VERSION, STORAGE_KEY)
        self._keys = keys

    async def async_load(self) -> RoomInsights:
        return RoomInsights.from_dict(self._keys.sections_to_names(await self._store.async_load(), SECTIONS))

    async def async_save(self, insights: RoomInsights) -> None:
        await self._store.async_save(self._keys.sections_to_ids(insights.to_dict(), SECTIONS))
