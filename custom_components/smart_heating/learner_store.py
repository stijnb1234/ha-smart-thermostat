"""Thin Home Assistant Store wrapper persisting the lead-time learner (keyed by Room id)."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .engine.learner import SCHEMA_VERSION, LeadTimeLearner
from .rooms import RoomKeys

STORAGE_KEY = "smart_heating.learned_lead_times"
SECTIONS = ("rooms",)


class LearnerStore:
    def __init__(self, hass: HomeAssistant, keys: RoomKeys) -> None:
        self._store: Store = Store(hass, SCHEMA_VERSION, STORAGE_KEY)
        self._keys = keys

    async def async_load(self) -> LeadTimeLearner:
        return LeadTimeLearner.from_dict(self._keys.sections_to_names(await self._store.async_load(), SECTIONS))

    async def async_save(self, learner: LeadTimeLearner) -> None:
        await self._store.async_save(self._keys.sections_to_ids(learner.to_dict(), SECTIONS))
