"""Thin Home Assistant Store wrapper persisting the lead-time learner."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .engine.learner import SCHEMA_VERSION, LeadTimeLearner

STORAGE_KEY = "smart_heating.learned_lead_times"


class LearnerStore:
    def __init__(self, hass: HomeAssistant) -> None:
        self._store: Store = Store(hass, SCHEMA_VERSION, STORAGE_KEY)

    async def async_load(self) -> LeadTimeLearner:
        return LeadTimeLearner.from_dict(await self._store.async_load())

    async def async_save(self, learner: LeadTimeLearner) -> None:
        await self._store.async_save(learner.to_dict())
