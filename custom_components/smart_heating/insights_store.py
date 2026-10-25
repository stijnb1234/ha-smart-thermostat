"""Thin Home Assistant Store wrapper persisting the learned Room insights."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .engine.insights import SCHEMA_VERSION, RoomInsights

STORAGE_KEY = "smart_heating.room_insights"


class InsightsStore:
    def __init__(self, hass: HomeAssistant) -> None:
        self._store: Store = Store(hass, SCHEMA_VERSION, STORAGE_KEY)

    async def async_load(self) -> RoomInsights:
        return RoomInsights.from_dict(await self._store.async_load())

    async def async_save(self, insights: RoomInsights) -> None:
        await self._store.async_save(insights.to_dict())
