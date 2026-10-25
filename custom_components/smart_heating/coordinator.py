"""Thin HA glue: runs the pure Controller on a timer and applies its Decision.

Gathering and decision logic live in controller.py, gather.py, warmup.py, arrival.py,
vacation_plan.py and explain.py (unit-tested). This file only reads states, calls adapters
and is covered by the Home Assistant smoke tests.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .alerts_adapter import AlertAdapter
from .apply import run_isolated
from .boiler_adapter import make_boiler_adapter
from .const import (
    CONF_ARRIVAL_ENTITIES,
    CONF_AUTO_ARRIVAL,
    CONF_OUTDOOR_ENTITY,
    CONF_PERSONS,
    CONF_VACATION_CALENDAR,
    CONF_VACATION_KEYWORDS,
    DEFAULT_AUTO_ARRIVAL,
    DEFAULT_VACATION_KEYWORDS,
    DOMAIN,
    UPDATE_INTERVAL_SECONDS,
)
from .controller import Controller, Cycle, Snapshot
from .engine import Commands, SensorReading
from .engine.window import recent_drop, window_history
from .gather import battery_is_low, parse_number
from .presence_adapter import PresenceAdapter, is_arriving
from .rooms import absent_rooms
from .settings import build_engine_config
from .trv_adapter import TrvAdapter
from .vacation_plan import parse_keywords, periods_from_events

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant, State

    from .commands_store import CommandsStore
    from .engine.insights import RoomInsights
    from .engine.learner import LeadTimeLearner
    from .insights_store import InsightsStore
    from .learner_store import LearnerStore
    from .trv_devices import TrvDevice

_LOGGER = logging.getLogger(__name__)
_UNAVAILABLE = ("unavailable", "unknown", None)
_PRESENT_STATES = ("home", "on")
INSIGHTS_SAVE_EVERY = timedelta(minutes=15)
CALENDAR_REFRESH_EVERY = timedelta(minutes=15)
CALENDAR_LOOKAHEAD = timedelta(days=120)
# Heading home counts once the ETA is within the longest lead time, but at least this.
MIN_ARRIVAL_HORIZON = timedelta(minutes=30)
DEFAULT_ARRIVAL_HORIZON = timedelta(minutes=70)


def _reported_at(state: State) -> datetime:
    return getattr(state, "last_reported", None) or state.last_updated


@dataclass
class Persistence:
    learner_store: LearnerStore
    learner: LeadTimeLearner
    commands_store: CommandsStore
    insights_store: InsightsStore
    insights: RoomInsights
    restored: Commands
    away_since: datetime | None


class SmartHeatingCoordinator(DataUpdateCoordinator[Cycle]):
    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        shared: dict[str, Any],
        persistence: Persistence,
        trv_devices: dict[str, TrvDevice],
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL_SECONDS),
        )
        opts = entry.options
        self._shared = shared
        self.lang: str = shared.get("lang", "en")
        self._opts = opts
        self._p = persistence
        config = build_engine_config(shared["rooms"], opts)
        self._battery_low_percent = config.alerts.battery_low_percent
        self.controller = Controller(
            config, persistence.learner, shared["boosts"], shared["manual_overrides"], persistence.insights
        )
        self._insights_saved = dt_util.utcnow()
        self._insights_pending = False
        self.trv_devices = trv_devices
        self._trv = TrvAdapter(hass, trv_devices)
        self._boiler = make_boiler_adapter(hass, dict(opts))
        occupants = [e for entities in shared["presence_entities"].values() for e in entities]
        self.presence = PresenceAdapter(
            hass,
            opts.get(CONF_PERSONS, []),
            opts.get(CONF_ARRIVAL_ENTITIES, []),
            auto_arrival=opts.get(CONF_AUTO_ARRIVAL, DEFAULT_AUTO_ARRIVAL),
            also_track=occupants,
        )
        self.alerts = AlertAdapter(hass, self.lang)
        self._vacation = shared["vacation"]
        self._calendar = opts.get(CONF_VACATION_CALENDAR)
        self._keywords = parse_keywords(opts.get(CONF_VACATION_KEYWORDS, DEFAULT_VACATION_KEYWORDS))
        self._calendar_fetched: datetime | None = None
        restored = persistence.restored
        self.controller.restore(restored, persistence.away_since)
        self._trv.restore(restored.trv_setpoints, restored.trv_written_at, restored.trv_previous)
        if self._boiler is not None:
            self._boiler.restore(restored.boiler_setpoint, restored.boiler_changed_at)
        self._prev_manual: frozenset[str] = frozenset(restored.trv_manual)
        self._prev_hold = restored.boiler_hold_until
        self._prev_paused: frozenset[str] = frozenset()
        self._last_seen: dict[str, datetime] = {}
        # Last good external reading, so a sensor that goes unavailable ages into a stale alert.
        self._last_external: dict[str, SensorReading] = {}

    @property
    def learner(self) -> LeadTimeLearner:
        return self._p.learner

    def _reading(self, entity_id: str | None, attr: str | None = None) -> SensorReading | None:
        state = self.hass.states.get(entity_id) if entity_id else None
        if state is None or state.state in _UNAVAILABLE:
            return None
        raw = state.attributes.get(attr) if attr else state.state
        value = parse_number(raw)
        return None if value is None else SensorReading(value, _reported_at(state))

    def _arrival_horizon(self) -> timedelta:
        if self.data is None or not self.data.lead_times:
            return DEFAULT_ARRIVAL_HORIZON
        return max(MIN_ARRIVAL_HORIZON, *self.data.lead_times.values())

    def _snapshot(self) -> Snapshot:
        # Local time: schedule windows are wall-clock times, the engine reads them off `now`.
        now = dt_util.now()
        external: dict[str, SensorReading] = {}
        trv: dict[str, SensorReading] = {}
        battery: dict[str, bool] = {}
        sensors = self._shared["sensor_entities"]
        # Floor-heating and open-radiator rooms have a sensor but no TRV.
        for room in [*self.trv_devices, *(r for r in sensors if r not in self.trv_devices)]:
            if (r := self._reading(sensors.get(room))) is not None:
                self._last_external[room] = r
            if room in self._last_external:
                external[room] = self._last_external[room]
            device = self.trv_devices.get(room)
            if device is None:
                continue
            if (r := self._reading(device.climate, "current_temperature")) is not None:
                trv[room] = r
            state = self.hass.states.get(device.climate)
            if state is not None and state.state not in _UNAVAILABLE:
                self._last_seen[room] = _reported_at(state)
            self._last_seen.setdefault(room, now)  # grace period at startup
            bat = self.hass.states.get(device.battery) if device.battery else None
            battery[room] = bat is not None and battery_is_low(bat.state, self._battery_low_percent)
        self.presence.update(self._arrival_horizon())
        anyone_home = self.presence.anyone_home(now)
        planner = self._vacation.planner
        manual_before = planner.manual
        vacation_until = planner.until(now, anyone_home)
        if manual_before is not None and planner.manual is None:  # back home: the switch turns off
            for entity in self._vacation.entities:
                if entity.hass is not None:
                    entity.async_write_ha_state()
        outdoor = self._reading(self._opts.get(CONF_OUTDOOR_ENTITY))
        return Snapshot(
            now=now,
            external=external,
            trv=trv,
            trv_last_seen=dict(self._last_seen),
            battery_low=battery,
            anyone_home=anyone_home,
            vacation_until=vacation_until,
            outdoor_temp=outdoor.value if outdoor else None,
            last_write=self._boiler.last_write if self._boiler else None,
            boiler_observed=self._boiler.observed_setpoint if self._boiler else None,
            absent_rooms=self._absent_rooms(now),
            trv_off=self._trv.stuck_off(),
            trv_observed={room: v for room in self.trv_devices if (v := self._trv.observed(room)) is not None},
        )

    def _absent_rooms(self, now: datetime) -> frozenset[str]:
        presence = self._shared["presence_entities"]
        heading_home = self.presence.arriving_people(now)
        known: dict[str, bool | None] = {}
        for entities in presence.values():
            for entity in entities:
                state = self.hass.states.get(entity)
                if entity in heading_home:
                    known[entity] = True  # on the way: warm the room up
                elif state is None or state.state in _UNAVAILABLE:
                    known[entity] = None
                else:
                    known[entity] = state.state in _PRESENT_STATES
        arrival = self._shared["arrival_entities"]
        arriving = {
            e: is_arriving(e, s.state if (s := self.hass.states.get(e)) else None)
            for entities in arrival.values()
            for e in entities
        }
        return absent_rooms(presence, known, arrival, arriving)

    async def _refresh_calendar(self) -> None:
        """Vacation periods from the calendar, fetched every 15 minutes."""
        now = dt_util.now()
        if not self._calendar or (
            self._calendar_fetched is not None and now - self._calendar_fetched < CALENDAR_REFRESH_EVERY
        ):
            return
        self._calendar_fetched = now
        try:
            response = await self.hass.services.async_call(
                "calendar",
                "get_events",
                {
                    "entity_id": self._calendar,
                    "start_date_time": (now - timedelta(minutes=1)).isoformat(),
                    "end_date_time": (now + CALENDAR_LOOKAHEAD).isoformat(),
                },
                blocking=True,
                return_response=True,
            )
        except Exception:
            _LOGGER.warning("Reading vacation calendar %s failed; keeping what was known", self._calendar, exc_info=True)
            return
        found: Any = (response or {}).get(self._calendar) or {}
        events = found.get("events", []) if isinstance(found, dict) else []
        self._vacation.planner.calendar = periods_from_events(events, self._keywords, now.tzinfo or dt_util.UTC)

    async def _async_update_data(self) -> Cycle:
        await self._refresh_calendar()
        snap = self._snapshot()
        cycle = self.controller.step(snap)
        decision = cycle.decision
        pushed: set[str] = set()

        async def push() -> None:
            pushed.update(await self._trv.async_push_external_temperature(decision.external_temp_pushes))

        async def boiler() -> None:
            if self._boiler is not None:
                await self._boiler.async_apply(decision.boiler_setpoint, decision.boiler_reassert)

        # Independent steps: one failing write must not skip the rest of the cycle.
        await run_isolated(
            [
                ("trv setpoints", lambda: self._trv.async_apply(decision.trv_setpoints, decision.trv_rewrite)),
                ("trv mode", self._trv.async_fix_modes),
                ("external temperature", push),
                ("boiler", boiler),
                ("alerts", lambda: self.alerts.async_apply(decision.alerts)),
            ],
            _LOGGER,
        )
        self.controller.confirm(
            cycle,
            self._trv.written,
            self._boiler.commands if self._boiler else Commands(),
            pushed,
            self._trv.written_at,
            self._trv.previous,
        )
        self._log_changes(cycle)
        self._p.commands_store.save_if_changed(self.controller.commands, self.controller.away_since)
        if self.controller.take_learner_dirty():
            await self._p.learner_store.async_save(self._p.learner)
        await self._save_insights()
        return cycle

    async def _save_insights(self, force: bool = False) -> None:
        """Insights change every few minutes; write them to disk at most every 15 minutes."""
        self._insights_pending = self.controller.take_insights_dirty() or self._insights_pending
        now = dt_util.utcnow()
        if self._insights_pending and (force or now - self._insights_saved >= INSIGHTS_SAVE_EVERY):
            await self._p.insights_store.async_save(self.controller.insights)
            self._insights_saved, self._insights_pending = now, False

    async def async_flush(self) -> None:
        """Write learned data that is waiting for its next periodic save (unload, stop)."""
        await self._save_insights(force=True)
        if self.controller.take_learner_dirty():
            await self._p.learner_store.async_save(self._p.learner)

    def _log_changes(self, cycle: Cycle) -> None:
        decision = cycle.decision
        manual = frozenset(decision.trv_manual)
        for room in manual - self._prev_manual:
            _LOGGER.info("TRV in %s was set by hand; leaving it alone until its target changes", room)
        for room in self._prev_manual - manual:
            _LOGGER.info("TRV in %s is back under Smart Heating control", room)
        hold = decision.boiler_hold_until
        if hold != self._prev_hold:
            if hold is not None:
                _LOGGER.info("Boiler thermostat was changed by hand; respecting it until %s", hold)
            else:
                _LOGGER.info("Boiler thermostat manual hold ended")
        paused = frozenset(decision.window_paused_until)
        rooms = {r.name: r for r in cycle.inp.config.rooms}
        for name in paused - self._prev_paused:
            cfg = rooms[name]
            cooling = name in cycle.inp.cooling_rooms
            drop = recent_drop(window_history(cfg, cycle.inp), cycle.inp.now, cfg.window_period)
            _LOGGER.info(
                "Open window in %s: %.1f K drop within %s min (%s sensor); pausing until %s",
                name,
                drop or 0.0,
                int(cfg.window_period.total_seconds() // 60),
                "external, radiator cooling" if cooling else "TRV-first",
                decision.window_paused_until[name],
            )
        self._prev_manual, self._prev_hold, self._prev_paused = manual, hold, paused
