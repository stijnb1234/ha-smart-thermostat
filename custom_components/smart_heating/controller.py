"""Pure control cycle: snapshot of the world in, Decision and explanations out.

Owns the state that must survive between cycles (temperature history, unmet
tracking, last commands, warm-up detection). The HA coordinator only builds the
Snapshot, applies the Decision through adapters and calls `confirm`.
No Home Assistant imports.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Collection, Mapping

from .engine import (
    Boost,
    Commands,
    Decision,
    EngineConfig,
    EngineInput,
    ManualRoomOverride,
    SensorReading,
    WriteResult,
    decide,
    lead_time_for,
    select_window_temperature,
    track_unmet,
    wants_comfort,
)
from .engine.insights import RoomInsights, Suggestion
from .engine.learner import LeadTimeLearner
from .engine.trackers import CoastTracker, StallTracker
from .engine.window import drop_threshold, recent_drop
from .explain import Explanation, explain
from .gather import update_history
from .warmup import WarmupTracker

HISTORY_KEEP = timedelta(minutes=30)
# Quiet-time samples for the learned insights are taken this often (not every cycle).
SAMPLE_EVERY = timedelta(minutes=5)


@dataclass(frozen=True)
class Snapshot:
    """Raw readings gathered from Home Assistant for one cycle."""

    now: datetime
    external: Mapping[str, SensorReading]
    trv: Mapping[str, SensorReading]
    trv_last_seen: Mapping[str, datetime]
    battery_low: Mapping[str, bool]
    anyone_home: bool
    away_since: datetime | None
    vacation_until: datetime | None
    outdoor_temp: float | None
    last_write: WriteResult | None
    easycontrol_observed: float | None = None
    trv_observed: Mapping[str, float] = field(default_factory=dict)
    absent_rooms: frozenset[str] = frozenset()
    trv_off: frozenset[str] = frozenset()


@dataclass(frozen=True)
class Cycle:
    inp: EngineInput
    decision: Decision
    explanations: Mapping[str, Explanation]
    lead_times: Mapping[str, timedelta]


class Controller:
    def __init__(
        self,
        config: EngineConfig,
        learner: LeadTimeLearner,
        boosts: Mapping[str, Boost],
        manual_overrides: Mapping[str, ManualRoomOverride],
        insights: RoomInsights | None = None,
    ) -> None:
        self._config = config
        self._learner = learner
        self.insights = insights or RoomInsights()
        self.insights_dirty = False
        self._coast = CoastTracker()
        self._stall = StallTracker()
        self._seen_boosts: dict[str, datetime] | None = None
        self._prev_hand: frozenset[str] = frozenset()
        self._last_sample: datetime | None = None
        self._boosts = boosts  # shared with the button entities, read live
        self._overrides = manual_overrides
        self._history: dict[str, tuple[SensorReading, ...]] = {}
        self._unmet: dict[str, datetime] = {}
        self._targets: dict[str, float] = {}
        self._commands = Commands()
        self._warmups = WarmupTracker()
        self.learner_dirty = False

    @property
    def commands(self) -> Commands:
        return self._commands

    def restore(self, commands: Commands) -> None:
        """Resume bookkeeping saved before a restart (manual changes, holds, retries)."""
        self._commands = commands

    def _record_history(self, snap: Snapshot) -> None:
        for room in self._config.rooms:
            value = select_window_temperature(
                room, snap.external, snap.trv, snap.now, self._config.sensors
            )
            if value is None:
                continue
            self._history[room.name] = update_history(
                self._history.get(room.name, ()),
                SensorReading(value, snap.now),
                snap.now,
                HISTORY_KEEP,
            )

    def step(self, snap: Snapshot) -> Cycle:
        self._record_history(snap)
        rooms = self._config.rooms
        lead_times: dict[str, timedelta] = {}
        learned: dict[str, timedelta] = {}
        if snap.outdoor_temp is not None:
            learned = self._learner.lead_times(
                snap.outdoor_temp, {r.name: r.comfort - r.setback for r in rooms}
            )
        for room in rooms:
            lead_times[room.name] = lead_time_for(room, learned)
        # Unmet tracking compares last cycle's temperatures with last cycle's targets.
        unmet_temps = {n: r.value for n, r in snap.trv.items()}
        unmet_temps.update({n: r.value for n, r in snap.external.items()})
        self._unmet = track_unmet(self._unmet, snap.now, unmet_temps, self._targets)
        inp = EngineInput(
            config=self._config,
            now=snap.now,
            anyone_home=snap.anyone_home,
            learned=learned,
            last_commands=self._commands,
            external_temps=snap.external,
            trv_temps=snap.trv,
            last_write=snap.last_write,
            easycontrol_observed=snap.easycontrol_observed,
            trv_observed=snap.trv_observed,
            trv_last_seen=snap.trv_last_seen,
            battery_low=snap.battery_low,
            unmet_since=self._unmet,
            boosts=self._boosts,
            manual_overrides=self._overrides,
            away_since=snap.away_since,
            absent_rooms=snap.absent_rooms,
            trv_off=snap.trv_off,
            vacation_until=snap.vacation_until,
            temp_history=dict(self._history),
            window_thresholds={
                r.name: t
                for r in rooms
                if (t := self.insights.window_threshold(r.name, r.window_drop)) is not None
            },
            coast={r.name: c for r in rooms if (c := self.insights.coast(r.name)) is not None},
            learned_offsets={
                r.name: o for r in rooms if (o := self.insights.offset(r.name)) is not None
            },
            stalled=self._stall.stalled(snap.now),
        )
        decision = decide(inp)
        self._targets = dict(decision.trv_setpoints)
        self._learn_insights(snap, inp, decision)
        for room in rooms:
            warm = self._warmups.observe(
                room.name,
                snap.now,
                decision.room_temps.get(room.name),
                decision.trv_setpoints[room.name],
                room.comfort,
                snap.outdoor_temp,
            )
            if warm is not None:
                self._learner.record_warmup(
                    warm.room, warm.outdoor_temp, warm.delta, warm.duration
                )
                self.learner_dirty = True
        explanations = {r.name: explain(r, inp, decision) for r in rooms}
        return Cycle(inp, decision, explanations, lead_times)

    def _learn_insights(self, snap: Snapshot, inp: EngineInput, decision: Decision) -> None:
        """Feed this cycle's observations to the stall/coast trackers and the insights."""
        ins, now = self.insights, snap.now
        calling = set(decision.demand_rooms)
        sample = self._last_sample is None or now - self._last_sample >= SAMPLE_EVERY
        if sample:
            self._last_sample = now
        for room in self._config.rooms:
            name = room.name
            temp = decision.room_temps.get(name)
            reason = decision.reasons[name]
            self._stall.observe(name, now, temp, name in calling)
            rise = self._coast.observe(
                name, now, temp, name in calling, valid=reason in ("schedule", "pre_heat")
            )
            if rise is not None:
                ins.record_coast(name, rise)
                self.insights_dirty = True
            if not sample:
                continue
            if room.window_detection and name not in decision.window_paused_until:
                drop = recent_drop(self._history.get(name, ()), now, room.window_period)
                if drop is not None and drop < drop_threshold(room, inp):
                    ins.record_drop(name, drop)
                    self.insights_dirty = True
            cfg = self._config.sensors
            ext, trv = snap.external.get(name), snap.trv.get(name)
            # Radiator idle (valve closed: room above the TRV's setpoint) so the TRV reads true.
            if (
                ext is not None
                and trv is not None
                and now - ext.at < cfg.external_stale_after
                and now - trv.at < cfg.trv_stale_after
                and ext.value > decision.trv_setpoints[name] + 0.2
            ):
                ins.record_offset(name, ext.value - trv.value)
                self.insights_dirty = True
        self._record_wishes(snap, decision)

    def _record_wishes(self, snap: Snapshot, decision: Decision) -> None:
        """Boosts and hand-set TRVs are wishes for warmth: input for schedule suggestions."""
        seen = self._seen_boosts
        self._seen_boosts = {name: b.start for name, b in self._boosts.items()}
        if seen is not None:  # first cycle only seeds: boosts restored after a restart are not new
            for name, start in self._seen_boosts.items():
                if seen.get(name) != start:
                    self.insights.record_event(name, snap.now)
                    self.insights_dirty = True
        setbacks = {r.name: r.setback for r in self._config.rooms}
        for name, value in decision.hand_set.items():
            if name not in self._prev_hand and value > setbacks.get(name, value):
                self.insights.record_event(name, snap.now)
                self.insights_dirty = True
        self._prev_hand = frozenset(decision.hand_set)

    def suggestions(self, now: datetime) -> list[Suggestion]:
        """Recurring wishes for warmth that no schedule window covers yet."""
        rooms = {r.name: r for r in self._config.rooms}
        return self.insights.suggestions(
            now, lambda name, at: name not in rooms or wants_comfort(rooms[name], at, {})
        )

    def take_insights_dirty(self) -> bool:
        dirty, self.insights_dirty = self.insights_dirty, False
        return dirty

    def confirm(
        self,
        cycle: Cycle,
        trv_written: Mapping[str, float],
        easycontrol: Commands,
        pushed_rooms: Collection[str] | None = None,
        trv_written_at: Mapping[str, datetime] | None = None,
        trv_previous: Mapping[str, float] | None = None,
    ) -> None:
        """Feed back what the adapters actually issued, for debounce and window pauses.

        `pushed_rooms` are the Rooms whose external temperature push succeeded (None: all).
        """
        now = cycle.inp.now
        pushed = dict(self._commands.external_temp_pushed)
        pushed_at = dict(self._commands.external_temp_pushed_at)
        for room, value in cycle.decision.external_temp_pushes.items():
            if pushed_rooms is not None and room not in pushed_rooms:
                continue
            pushed[room] = value
            pushed_at[room] = now
        self._commands = Commands(
            trv_setpoints=dict(trv_written),
            easycontrol_setpoint=easycontrol.easycontrol_setpoint,
            easycontrol_changed_at=easycontrol.easycontrol_changed_at,
            easycontrol_hold_until=cycle.decision.easycontrol_hold_until,
            trv_written_at=dict(trv_written_at or {}),
            trv_previous=dict(trv_previous or {}),
            trv_retries=dict(cycle.decision.trv_retries),
            trv_manual=dict(cycle.decision.trv_manual),
            external_temp_pushed=pushed,
            external_temp_pushed_at=pushed_at,
            window_paused_until=dict(cycle.decision.window_paused_until),
        )

    def take_learner_dirty(self) -> bool:
        dirty, self.learner_dirty = self.learner_dirty, False
        return dirty
