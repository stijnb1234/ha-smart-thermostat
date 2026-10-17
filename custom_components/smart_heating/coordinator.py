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
from .apply import run_isolated
from .const import (
    CONF_EASYCONTROL_ENTITY,
    CONF_OUTDOOR_ENTITY,
    CONF_ARRIVAL_ENTITIES,
    CONF_PERSONS,
    DOMAIN,
    UPDATE_INTERVAL_SECONDS,
)
from .controller import Controller, Cycle, Snapshot
from .easycontrol_adapter import EasyControlAdapter
from .engine import Commands, SensorReading
from .gather import battery_entity, battery_is_low, parse_number, z2m_name
from .learner_store import LearnerStore
from .presence_adapter import PresenceAdapter
from .rooms import absent_rooms
from .settings import build_engine_config
from .trv_adapter import TrvAdapter

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant, State

_LOGGER = logging.getLogger(__name__)
_UNAVAILABLE = ("unavailable", "unknown", None)
_PRESENT_STATES = ("home", "on")
# A heading-home entity is active in any state but these (a person in a zone has the zone name).
_NOT_ARRIVING = ("not_home", "off", "unavailable", "unknown")


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
        commands_store=None,
        restored: Commands | None = None,
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
        config = build_engine_config(shared["rooms"], opts)
        self._battery_low_percent = config.alerts.battery_low_percent
        self.controller = Controller(
            config, learner, shared["boosts"], shared["manual_overrides"]
        )
        self._trv = TrvAdapter(hass, shared["trv_entities"])
        ec_entity = opts.get(CONF_EASYCONTROL_ENTITY)
        self._ec = EasyControlAdapter(hass, ec_entity) if ec_entity else None
        self._presence = PresenceAdapter(
            hass, opts.get(CONF_PERSONS, []), opts.get(CONF_ARRIVAL_ENTITIES, [])
        )
        self.alerts = AlertAdapter(hass)
        self._commands_store = commands_store
        self._prev_manual: frozenset[str] = frozenset()
        self._prev_hold = None
        if restored is not None:
            self.controller.restore(restored)
            self._trv.restore(
                restored.trv_setpoints, restored.trv_written_at, restored.trv_previous
            )
            if self._ec is not None:
                self._ec.restore(restored.easycontrol_setpoint, restored.easycontrol_changed_at)
            self._prev_manual = frozenset(restored.trv_manual)
            self._prev_hold = restored.easycontrol_hold_until
        self._z2m = {room: z2m_name(e) for room, e in shared["trv_entities"].items()}
        self._last_seen: dict[str, datetime] = {}
        # Last good external reading, so a sensor that goes unavailable ages into a stale alert.
        self._last_external: dict[str, SensorReading] = {}

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
        trv_by_room = self._shared["trv_entities"]
        # Floor-heating rooms have a sensor but no TRV.
        for room in [*trv_by_room, *(r for r in self._shared["sensor_entities"] if r not in trv_by_room)]:
            trv_entity = trv_by_room.get(room)
            if (r := self._reading(self._shared["sensor_entities"].get(room))) is not None:
                self._last_external[room] = r
            if room in self._last_external:
                external[room] = self._last_external[room]
            if trv_entity is None:
                continue
            if (r := self._reading(trv_entity, "current_temperature")) is not None:
                trv[room] = r
            state = self.hass.states.get(trv_entity)
            if state is not None and state.state not in _UNAVAILABLE:
                self._last_seen[room] = _reported_at(state)
            self._last_seen.setdefault(room, now)  # grace period at startup
            bat = self.hass.states.get(battery_entity(trv_entity))
            battery[room] = bat is not None and battery_is_low(bat.state, self._battery_low_percent)
        trv_entities = self._shared["trv_entities"]
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
            easycontrol_observed=self._ec.observed_setpoint if self._ec else None,
            absent_rooms=self._absent_rooms(),
            trv_off=self._trv.stuck_off(),
            trv_observed={
                room: v for room in trv_entities if (v := self._trv.observed(room)) is not None
            },
        )

    def _absent_rooms(self) -> frozenset[str]:
        presence = self._shared["presence_entities"]
        known: dict[str, bool | None] = {}
        for entities in presence.values():
            for entity in entities:
                state = self.hass.states.get(entity)
                known[entity] = (
                    None
                    if state is None or state.state in _UNAVAILABLE
                    else state.state in _PRESENT_STATES
                )
        arrival = self._shared["arrival_entities"]
        arriving = {
            e: (s := self.hass.states.get(e)) is not None and s.state not in _NOT_ARRIVING
            for entities in arrival.values()
            for e in entities
        }
        return absent_rooms(presence, known, arrival, arriving)

    async def _async_update_data(self) -> Cycle:
        snap = self._snapshot()
        cycle = self.controller.step(snap)
        decision = cycle.decision
        pushed: set[str] = set()

        async def push() -> None:
            pushed.update(
                await self._trv.async_push_external_temperature(
                    decision.external_temp_pushes, self._z2m
                )
            )

        async def boiler() -> None:
            if self._ec is not None:
                await self._ec.async_apply(
                    decision.easycontrol_setpoint, decision.easycontrol_reassert
                )

        # Independent steps: one failing write must not skip the rest of the cycle.
        await run_isolated(
            [
                ("trv setpoints", lambda: self._trv.async_apply(decision.trv_setpoints, decision.trv_rewrite)),
                ("trv mode", self._trv.async_fix_modes),
                ("external temperature", push),
                ("easycontrol", boiler),
                ("alerts", lambda: self.alerts.async_apply(decision.alerts)),
            ],
            _LOGGER,
        )
        self.controller.confirm(
            cycle,
            self._trv.written,
            self._ec.commands if self._ec else Commands(),
            pushed,
            self._trv.written_at,
            self._trv.previous,
        )
        self._log_manual_changes(decision)
        if self._commands_store is not None:
            self._commands_store.save_if_changed(self.controller.commands)
        if self.controller.take_learner_dirty():
            await self._store.async_save(self._learner)
        await self._clear_finished_vacation(snap)
        return cycle

    def _log_manual_changes(self, decision) -> None:
        manual = frozenset(decision.trv_manual)
        for room in manual - self._prev_manual:
            _LOGGER.info("TRV in %s was set by hand; leaving it alone until its target changes", room)
        for room in self._prev_manual - manual:
            _LOGGER.info("TRV in %s is back under Smart Heating control", room)
        hold = decision.easycontrol_hold_until
        if hold != self._prev_hold:
            if hold is not None:
                _LOGGER.info("EasyControl was changed by hand; respecting it until %s", hold)
            else:
                _LOGGER.info("EasyControl manual hold ended")
        self._prev_manual, self._prev_hold = manual, hold

    async def _clear_finished_vacation(self, snap: Snapshot) -> None:
        vacation = self._shared["vacation"]
        if vacation.until is None or snap.now < vacation.until or not snap.anyone_home:
            return
        if vacation.switch is not None:
            await vacation.switch.async_clear()
        else:
            vacation.until = None
