"""Thin HA glue: binary sensor that is on while the boiler call is active."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .dashboard import entity_id
from .status import boiler_status


class BoilerCallSensor(CoordinatorEntity, BinarySensorEntity):
    _attr_name = "Smart Heating boiler called"

    def __init__(self, coordinator, entry_id: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry_id}_boiler_call"
        self.entity_id = entity_id("binary_sensor", None, "boiler_call")

    @property
    def is_on(self) -> bool | None:
        data = self.coordinator.data
        return boiler_status(data.inp, data.decision).call_active if data else None


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    shared = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([BoilerCallSensor(shared["coordinator"], entry.entry_id)])
