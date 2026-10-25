"""Vacation mode entities: the return moment (a date-time) and a switch.

Thin glue over vacation_plan.VacationPlanner. Pick when you are back, turn the switch on: the
house holds frost-hold from now until each Room has to start warming up for your return.
Vacation can also come from a calendar (options) or the `smart_heating.set_vacation` service.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.components.datetime import DateTimeEntity
from homeassistant.components.switch import SwitchEntity
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .i18n import tr
from .vacation_plan import VacationPeriod, VacationPlanner

if TYPE_CHECKING:
    from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

DEFAULT_RETURN_AFTER = timedelta(days=7)


class VacationState:
    """Shared between the entities, the services and the coordinator."""

    def __init__(self) -> None:
        self.planner = VacationPlanner()
        self.return_draft: datetime | None = None  # picked before the switch is turned on
        self.entities: list[Any] = []
        self.coordinator: DataUpdateCoordinator | None = None

    def set_manual(self, period: VacationPeriod | None) -> None:
        self.planner.manual = period
        if period is not None:
            self.return_draft = period.end
        self.refresh()

    def refresh(self) -> None:
        for entity in self.entities:
            if entity.hass is not None:
                entity.async_write_ha_state()
        if self.coordinator is not None:
            self.coordinator.hass.async_create_task(self.coordinator.async_request_refresh())


class VacationReturnDateTime(DateTimeEntity, RestoreEntity):
    """When the household is back. Editing it moves the return of a running vacation."""

    entity_id = "datetime.smart_heating_vacation_return"

    def __init__(self, state: VacationState, entry_id: str, lang: str = "en") -> None:
        self._state = state
        self._attr_name = tr(lang, "entity.vacation_return")
        self._attr_unique_id = f"{entry_id}_vacation_return"
        self._attr_icon = "mdi:airplane-landing"
        state.entities.append(self)

    @property
    def native_value(self) -> datetime | None:
        manual = self._state.planner.manual
        return manual.end if manual is not None else self._state.return_draft

    async def async_added_to_hass(self) -> None:
        last = await self.async_get_last_state()
        if self._state.return_draft is None and last is not None:
            self._state.return_draft = dt_util.parse_datetime(last.state)

    async def async_set_value(self, value: datetime) -> None:
        manual = self._state.planner.manual
        if manual is not None:
            if value <= manual.start:
                raise ServiceValidationError(translation_domain=DOMAIN, translation_key="return_before_start")
            self._state.set_manual(VacationPeriod(manual.start, value))
        else:
            self._state.return_draft = value
            self.async_write_ha_state()


class VacationSwitch(SwitchEntity, RestoreEntity):
    """On while a manual vacation is set (running or planned)."""

    entity_id = "switch.smart_heating_vacation_mode"

    def __init__(self, state: VacationState, entry_id: str, lang: str = "en") -> None:
        self._state = state
        self._attr_name = tr(lang, "entity.vacation_mode")
        self._attr_unique_id = f"{entry_id}_vacation_mode"
        self._attr_icon = "mdi:palm-tree"
        state.entities.append(self)

    @property
    def is_on(self) -> bool:
        return self._state.planner.manual is not None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        manual = self._state.planner.manual
        now = dt_util.now()
        upcoming = self._state.planner.upcoming(now)
        return {
            "start": manual.start.isoformat() if manual else None,
            "until": manual.end.isoformat() if manual else None,
            "calendar_periods": [p.to_dict() for p in self._state.planner.calendar if p.end > now],
            "next_vacation": upcoming.to_dict() if upcoming else None,
        }

    async def async_added_to_hass(self) -> None:
        last = await self.async_get_last_state()
        if last is None or last.state != "on" or self._state.planner.manual is not None:
            return
        attrs = last.attributes
        until = dt_util.parse_datetime(attrs.get("until") or "")
        start = dt_util.parse_datetime(attrs.get("start") or "") or last.last_changed
        if until is not None and start < until:
            self._state.planner.manual = VacationPeriod(start, until)

    async def async_turn_on(self, **kwargs: Any) -> None:
        now = dt_util.now()
        back = self._state.return_draft or now + DEFAULT_RETURN_AFTER  # nothing picked yet: a week
        if back <= now:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="return_in_past")
        self._state.set_manual(VacationPeriod(now, back))

    async def async_turn_off(self, **kwargs: Any) -> None:
        self._state.set_manual(None)
