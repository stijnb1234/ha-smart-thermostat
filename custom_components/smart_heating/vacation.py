"""Vacation mode entities: a number (days) and a switch (on/off).

Thin glue. Turning the switch on stores `vacation_end(now, days)`; the
coordinator passes it as `EngineInput.vacation_until`, and clears it
(`async_clear`) once someone is home again.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from homeassistant.components.number import NumberEntity, RestoreNumber
from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import dt as dt_util

from .engine import vacation_end

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback


class VacationState:
    """Shared between the number and the switch entity."""

    def __init__(self) -> None:
        self.days = 7
        self.until: datetime | None = None
        self.switch: VacationSwitch | None = None


class VacationDaysNumber(RestoreNumber, NumberEntity):
    _attr_name = "Vacation days"
    entity_id = "number.smart_heating_vacation_days"
    _attr_native_min_value = 1
    _attr_native_max_value = 60
    _attr_native_step = 1
    _attr_native_value = 7

    def __init__(self, state: VacationState) -> None:
        self._state = state

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last := await self.async_get_last_number_data()) is not None:
            if last.native_value is not None:
                self._attr_native_value = last.native_value
                self._state.days = int(last.native_value)

    async def async_set_native_value(self, value: float) -> None:
        self._attr_native_value = value
        self._state.days = int(value)
        self.async_write_ha_state()


class VacationSwitch(SwitchEntity, RestoreEntity):
    _attr_name = "Vacation mode"
    entity_id = "switch.smart_heating_vacation_mode"

    def __init__(self, state: VacationState) -> None:
        self._state = state
        state.switch = self

    @property
    def is_on(self) -> bool:
        return self._state.until is not None

    async def async_added_to_hass(self) -> None:
        last = await self.async_get_last_state()
        until = last.attributes.get("until") if last else None
        if until:
            self._state.until = dt_util.parse_datetime(until)

    @property
    def extra_state_attributes(self) -> dict[str, str | None]:
        until = self._state.until
        return {"until": until.isoformat() if until else None}

    async def async_turn_on(self, **kwargs) -> None:
        self._state.until = vacation_end(dt_util.now(), self._state.days)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        await self.async_clear()

    async def async_clear(self) -> None:
        self._state.until = None
        self.async_write_ha_state()


async def async_add_vacation_entities(
    hass: HomeAssistant, entry: ConfigEntry, add: AddEntitiesCallback
) -> VacationState:
    state = VacationState()
    add([VacationDaysNumber(state), VacationSwitch(state)])
    return state
