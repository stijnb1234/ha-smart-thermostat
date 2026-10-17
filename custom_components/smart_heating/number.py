"""Thin HA glue: Vacation days number (entity lives in vacation.py)."""

from __future__ import annotations

from .const import DOMAIN
from .vacation import VacationDaysNumber


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    shared = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([VacationDaysNumber(shared["vacation"], shared["lang"])])
