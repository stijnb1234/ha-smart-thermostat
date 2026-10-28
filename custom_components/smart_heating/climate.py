"""Thin HA glue: a read-only climate entity per Room showing engine target and current temperature.

Targets come from the schedule, Boost, Away and Vacation, so they are changed
through those (and the options flow); setting a temperature here is refused with an explanation.
The `smart_heating.boost` / `cancel_boost` services target these entities.
"""

from __future__ import annotations

import voluptuous as vol
from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.const import UnitOfTemperature
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_platform
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .button import cancel_boost, start_boost
from .const import DOMAIN
from .coordinator import SmartHeatingCoordinator
from .dashboard import entity_id
from .engine import RoomConfig
from .i18n import tr
from .status import room_heating

ATTR_DURATION = "duration"



class RoomClimate(CoordinatorEntity[SmartHeatingCoordinator], ClimateEntity):
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_modes = [HVACMode.HEAT]
    _attr_hvac_mode = HVACMode.HEAT
    # HA only exposes the `temperature` attribute (shown as "wanted temperature") when this
    # feature is set. Setting it is refused below: the target is decided by the engine.
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE

    def __init__(self, coordinator, entry_id: str, room: RoomConfig, shared: dict) -> None:
        super().__init__(coordinator)
        self._room = room.name
        self._shared = shared
        self._attr_name = room.name
        self._attr_unique_id = f"{entry_id}_climate_{room.id}"
        self.entity_id = entity_id("climate", room.id)

    @property
    def current_temperature(self) -> float | None:
        data = self.coordinator.data
        return data.decision.room_temps.get(self._room) if data else None

    @property
    def target_temperature(self) -> float | None:
        data = self.coordinator.data
        if not data:
            return None
        d = data.decision
        return d.hand_set.get(self._room, d.satisfied_targets.get(self._room, d.trv_setpoints.get(self._room)))

    async def async_set_temperature(self, **kwargs) -> None:
        raise ServiceValidationError(tr(self.coordinator.lang, "climate.set_refused"))

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        return None

    async def async_boost(self, duration=None) -> None:
        """Service: heat this Room to comfort now, for `duration` (default: the configured Boost)."""
        await start_boost(self._shared, self._room, duration or self._shared["boost_duration"])

    async def async_cancel_boost(self) -> None:
        await cancel_boost(self._shared, self._room)

    @property
    def hvac_action(self) -> HVACAction | None:
        """Heating while this Room actually calls the boiler (see status.room_heating)."""
        data = self.coordinator.data
        if not data or self._room not in data.decision.room_temps:
            return None
        heating = room_heating(self._room, data.inp, data.decision, self.coordinator.has_boiler)
        return HVACAction.HEATING if heating else HVACAction.IDLE

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        data = self.coordinator.data
        return {"reason": data.explanations[self._room].reason} if data else {}


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    shared = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        RoomClimate(shared["coordinator"], entry.entry_id, r, shared) for r in shared["rooms"]
    )
    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        "boost",
        {vol.Optional(ATTR_DURATION): vol.All(cv.time_period, cv.positive_timedelta)},
        "async_boost",
    )
    platform.async_register_entity_service("cancel_boost", None, "async_cancel_boost")
