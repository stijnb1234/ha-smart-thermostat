"""Thin HA glue: runs the pure Controller on a timer and applies its Decision.

Gathering and decision logic live in controller.py, gather.py, warmup.py and
explain.py (unit-tested). This file only reads states, calls adapters and is
verified in a real HA only.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .alerts_adapter import AlertAdapter
from .const import (
    CONF_EASYCONTROL_ENTITY,
    CONF_EASYCONTROL_HIGH,
    CONF_EASYCONTROL_LOW,
    CONF_OUTDOOR_ENTITY,
    CONF_PERSONS,
    DEFAULT_EASYCONTROL_HIGH,
    DEFAULT_EASYCONTROL_LOW,
    DOMAIN,
    UPDATE_INTERVAL_SECONDS,
)
from .controller import Controller, Cycle, Snapshot
from .easycontrol_adapter import EasyControlAdapter
from .engine import Commands, EngineConfig, SensorReading
from .gather import battery_entity, battery_is_low, parse_number, z2m_name
from .learner_store import LearnerStore
from .presence_adapter import PresenceAdapter
from .trv_adapter import TrvAdapter

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant, State

_LOGGER = logging.getLogger(__name__)
_UNAVAILABLE = ("unavailable", "unknown", None)


def _reported_at(state: State) -> datetime:
    return getattr(state, "last_reported", None) or state.last_updated


class SmartHeatingCoordinator(DataUpdateCoordinator[Cycle]):
    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        shared: dict[str, Any],
        learner_store: LearnerStore,
        learner,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL_SECONDS),
        )
        opts = entry.options
        self._shared = shared
        self._opts = opts
        self._store = learner_store
        self._learner = learner
        config = EngineConfig(
            rooms=shared["rooms"],
            easycontrol_low=float(opts.get(CONF_EASYCONTROL_LOW, DEFAULT_EASYCONTROL_LOW)),
            easycontrol_high=float(opts.get(CONF_EASYCONTROL_HIGH, DEFAULT_EASYCONTROL_HIGH)),
        )
        self.controller = Controller(
            config, learner, shared["boosts"], shared["manual_overrides"]
        )
        self._trv = TrvAdapter(hass, shared["trv_entities"])
        ec_entity = opts.get(CONF_EASYCONTROL_ENTITY)
        self._ec = EasyControlAdapter(hass, ec_entity) if ec_entity else None
        self._presence = PresenceAdapter(hass, opts.get(CONF_PERSONS, []))
        self._alerts = AlertAdapter(hass)
        self._z2m = {room: z2m_name(e) for room, e in shared["trv_entities"].items()}
        self._last_seen: dict[str, datetime] = {}

    def _reading(self, entity_id: str | None, attr: str | None = None) -> SensorReading | None:
        state = self.hass.states.get(entity_id) if entity_id else None
        if state is None or state.state in _UNAVAILABLE:
            return None
        raw = state.attributes.get(attr) if attr else state.state
        value = parse_number(raw)
        return None if value is None else SensorReading(value, _reported_at(state))

    def _snapshot(self) -> Snapshot:
        now = dt_util.utcnow()
        external: dict[str, SensorReading] = {}
        trv: dict[str, SensorReading] = {}
        battery: dict[str, bool] = {}
        for room, trv_entity in self._shared["trv_entities"].items():
            if (r := self._reading(self._shared["sensor_entities"].get(room))) is not None:
                external[room] = r
            if (r := self._reading(trv_entity, "current_temperature")) is not None:
                trv[room] = r
            state = self.hass.states.get(trv_entity)
            if state is not None and state.state not in _UNAVAILABLE:
                self._last_seen[room] = _reported_at(state)
            self._last_seen.setdefault(room, now)  # grace period at startup
            bat = self.hass.states.get(battery_entity(trv_entity))
            battery[room] = bat is not None and battery_is_low(bat.state)
        vacation = self._shared["vacation"]
        outdoor = self._reading(self._opts.get(CONF_OUTDOOR_ENTITY))
        return Snapshot(
            now=now,
            external=external,
            trv=trv,
            trv_last_seen=dict(self._last_seen),
            battery_low=battery,
            anyone_home=self._presence.anyone_home(),
            away_since=self._presence.away_since(),
            vacation_until=vacation.until,
            outdoor_temp=outdoor.value if outdoor else None,
            last_write=self._ec.last_write if self._ec else None,
        )

    async def _async_update_data(self) -> Cycle:
        snap = self._snapshot()
        cycle = self.controller.step(snap)
        decision = cycle.decision
        try:
            await self._trv.async_apply(decision.trv_setpoints)
            await self._trv.async_push_external_temperature(
                decision.external_temp_pushes, self._z2m
            )
            if self._ec is not None:
                await self._ec.async_apply(decision.easycontrol_setpoint)
            await self._alerts.async_apply(decision.alerts)
        except Exception:  # noqa: BLE001 - keep the loop alive; retried next cycle
            _LOGGER.exception("Applying smart heating decision failed")
        self.controller.confirm(
            cycle, self._trv.written, self._ec.commands if self._ec else Commands()
        )
        if self.controller.take_learner_dirty():
            await self._store.async_save(self._learner)
        await self._clear_finished_vacation(snap)
        return cycle

    async def _clear_finished_vacation(self, snap: Snapshot) -> None:
        vacation = self._shared["vacation"]
        if vacation.until is None or snap.now < vacation.until or not snap.anyone_home:
            return
        if vacation.switch is not None:
            await vacation.switch.async_clear()
        else:
            vacation.until = None
