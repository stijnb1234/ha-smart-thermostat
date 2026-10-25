"""Thin HA glue: Vacation return date-time (entity lives in vacation.py)."""

from __future__ import annotations

from .const import DOMAIN
from .vacation import VacationReturnDateTime


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    shared = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([VacationReturnDateTime(shared["vacation"], entry.entry_id, shared["lang"])])
