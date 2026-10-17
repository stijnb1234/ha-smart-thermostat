"""Thin HA glue: per Room sensors for the state reason, next change and pre-heat lead time."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import UnitOfTime
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .dashboard import entity_id

REASONS = ["boost", "window", "vacation", "away", "pre_heat", "schedule", "setback"]


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


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    shared = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        cls(shared["coordinator"], entry.entry_id, r.name)
        for r in shared["rooms"]
        for cls in (ReasonSensor, NextChangeSensor, LeadTimeSensor)
    )
