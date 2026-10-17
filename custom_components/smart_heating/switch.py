"""Thin HA glue: Vacation mode switch (entity lives in vacation.py)."""

from __future__ import annotations

from .const import DOMAIN
from .vacation import VacationSwitch


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    shared = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([VacationSwitch(shared["vacation"], shared["lang"])])
