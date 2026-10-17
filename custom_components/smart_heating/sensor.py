"""Thin HA glue: per Room sensors for the state reason, next change and pre-heat lead time."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import UnitOfTemperature, UnitOfTime
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .dashboard import entity_id
from .explain import summarize
from .status import (
    alert_sentence,
    backoff_text,
    hold_text,
    boiler_status,
    demand_text,
    heating_rooms,
    status_text,
)

REASONS = ["boost", "window", "vacation", "away", "occupant_away", "pre_heat", "schedule", "setback"]


class _RoomSensor(CoordinatorEntity, SensorEntity):
    key = ""
    label = ""

    def __init__(self, coordinator, entry_id: str, room: str) -> None:
        super().__init__(coordinator)
        self._room = room
        self._attr_name = f"{room} {self.label}"
        self._attr_unique_id = f"{entry_id}_{self.key}_{room}"
        self.entity_id = entity_id("sensor", room, self.key)

    @property
    def _explanation(self):
        data = self.coordinator.data
        return data.explanations.get(self._room) if data else None


class ReasonSensor(_RoomSensor):
    key, label = "reason", "heating reason"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = REASONS

    @property
    def native_value(self) -> str | None:
        e = self._explanation
        return e.reason if e else None


class SummarySensor(_RoomSensor):
    """Plain-language sentence about the room's target (the reason sensor stays machine-readable)."""

    key, label = "summary", "summary"

    @property
    def native_value(self) -> str | None:
        e = self._explanation
        if e is None:
            return None
        now = dt_util.as_local(self.coordinator.data.inp.now)
        if e.next_change_at is not None:
            e = replace(e, next_change_at=dt_util.as_local(e.next_change_at))
        return summarize(e, now)


class NextChangeSensor(_RoomSensor):
    key, label = "next_change", "next change"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    @property
    def native_value(self) -> datetime | None:
        e = self._explanation
        return e.next_change_at if e else None

    @property
    def extra_state_attributes(self) -> dict[str, float | None]:
        e = self._explanation
        return {"next_target": e.next_change_target if e else None}


class LeadTimeSensor(_RoomSensor):
    key, label = "lead_time", "pre-heat lead time"
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES

    @property
    def native_value(self) -> int | None:
        data = self.coordinator.data
        lead = data.lead_times.get(self._room) if data else None
        return round(lead.total_seconds() / 60) if lead else None


class _SystemSensor(CoordinatorEntity, SensorEntity):
    """System-wide sensor: smart_heating_<key>."""

    key = ""
    label = ""

    def __init__(self, coordinator, entry_id: str) -> None:
        super().__init__(coordinator)
        self._attr_name = f"Smart Heating {self.label}"
        self._attr_unique_id = f"{entry_id}_{self.key}"
        self.entity_id = entity_id("sensor", None, self.key)

    @property
    def _boiler(self):
        data = self.coordinator.data
        return boiler_status(data.inp, data.decision) if data else None


class StatusSensor(_SystemSensor):
    key, label = "status", "status"

    def _facts(self):
        data = self.coordinator.data
        inp, decision = data.inp, data.decision
        heating = heating_rooms(inp.config, decision.trv_setpoints, decision.room_temps)
        on = boiler_status(inp, decision).call_active
        vacation = inp.vacation_until is not None
        return heating, on, vacation, not inp.anyone_home

    @property
    def native_value(self) -> str | None:
        return status_text(*self._facts()) if self.coordinator.data else None

    @property
    def extra_state_attributes(self) -> dict:
        if not self.coordinator.data:
            return {}
        heating, on, vacation, away = self._facts()
        return {
            "heating_rooms": list(heating),
            "boiler_on": on,
            "vacation": vacation,
            "away": away,
        }


class ActiveAlertsSensor(_SystemSensor):
    key, label = "active_alerts", "active alerts"
    _attr_native_unit_of_measurement = "alerts"

    @property
    def _alerts(self):
        data = self.coordinator.data
        return data.decision.alerts if data else ()

    @property
    def native_value(self) -> int | None:
        return len(self._alerts) if self.coordinator.data else None

    @property
    def extra_state_attributes(self) -> dict:
        return {
            "messages": [alert_sentence(a) for a in self._alerts],
            "alerts": [{"code": a.code, "room": a.room} for a in self._alerts],
        }


class BoilerDemandSensor(_SystemSensor):
    key, label = "boiler_demand_rooms", "boiler demand from"

    @property
    def native_value(self) -> str | None:
        b = self._boiler
        return demand_text(b) if b else None

    @property
    def extra_state_attributes(self) -> dict:
        b = self._boiler
        return {"rooms": list(b.demand_rooms) if b else []}


class BoilerTargetSensor(_SystemSensor):
    key, label = "boiler_target", "boiler target (EasyControl)"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    @property
    def native_value(self) -> float | None:
        b = self._boiler
        return b.held_setpoint if b else None


class BoilerLastWriteSensor(_SystemSensor):
    key, label = "boiler_last_write", "boiler last write"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    @property
    def native_value(self) -> datetime | None:
        b = self._boiler
        return b.last_write_at if b else None


class BoilerWriteResultSensor(_SystemSensor):
    key, label = "boiler_write_result", "boiler last write result"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["ok", "rate_limited", "error", "none"]

    @property
    def native_value(self) -> str | None:
        b = self._boiler
        return b.last_write_result if b else None


class BoilerBackoffSensor(_SystemSensor):
    key, label = "boiler_backoff", "boiler backoff"

    @property
    def native_value(self) -> str | None:
        b = self._boiler
        if b is None:
            return None
        now = dt_util.as_local(self.coordinator.data.inp.now)
        until = dt_util.as_local(b.backoff_until) if b.backoff_until else None
        return backoff_text(until, now)


class BoilerManualHoldSensor(_SystemSensor):
    key, label = "boiler_manual_hold", "boiler manual hold"

    @property
    def native_value(self) -> str | None:
        b = self._boiler
        if b is None:
            return None
        now = dt_util.as_local(self.coordinator.data.inp.now)
        until = dt_util.as_local(b.hold_until) if b.hold_until else None
        return hold_text(until, now)


SYSTEM_SENSORS = (
    StatusSensor,
    ActiveAlertsSensor,
    BoilerDemandSensor,
    BoilerTargetSensor,
    BoilerLastWriteSensor,
    BoilerWriteResultSensor,
    BoilerBackoffSensor,
    BoilerManualHoldSensor,
)


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    shared = hass.data[DOMAIN][entry.entry_id]
    coordinator = shared["coordinator"]
    async_add_entities(
        cls(coordinator, entry.entry_id, r.name)
        for r in shared["rooms"]
        for cls in (ReasonSensor, SummarySensor, NextChangeSensor, LeadTimeSensor)
    )
    async_add_entities(cls(coordinator, entry.entry_id) for cls in SYSTEM_SENSORS)
