"""Thin HA glue: a read-only climate entity per Room showing engine target and current temperature.

Targets come from the schedule, Boost, Away and Vacation, so they are changed
through those (and the options flow), not by setting a temperature here.
"""

from __future__ import annotations

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.const import UnitOfTemperature
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .dashboard import entity_id


class RoomClimate(CoordinatorEntity, ClimateEntity):
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_modes = [HVACMode.HEAT]
    _attr_hvac_mode = HVACMode.HEAT
    _attr_supported_features = ClimateEntityFeature(0)

    def __init__(self, coordinator, entry_id: str, room: str) -> None:
        super().__init__(coordinator)
        self._room = room
        self._attr_name = room
        self._attr_unique_id = f"{entry_id}_climate_{room}"
        self.entity_id = entity_id("climate", room)

    @property
    def current_temperature(self) -> float | None:
        data = self.coordinator.data
        return data.decision.room_temps.get(self._room) if data else None

    @property
    def target_temperature(self) -> float | None:
        data = self.coordinator.data
        return data.decision.trv_setpoints.get(self._room) if data else None

    @property
    def hvac_action(self) -> HVACAction | None:
        cur, target = self.current_temperature, self.target_temperature
        if cur is None or target is None:
            return None
        return HVACAction.HEATING if cur < target else HVACAction.IDLE

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        data = self.coordinator.data
        return {"reason": data.explanations[self._room].reason} if data else {}


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    shared = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        RoomClimate(shared["coordinator"], entry.entry_id, r.name) for r in shared["rooms"]
    )
