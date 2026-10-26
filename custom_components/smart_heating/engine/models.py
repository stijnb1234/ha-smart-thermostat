"""Input and output types of the decision engine (the single test seam)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from typing import Literal

from .overrides import Boost, ManualRoomOverride

# Float comparison tolerance for thresholds.
EPSILON = 1e-9

# Default targets (spec: comfort 19.5, setback 16, frost-hold 12). The single place for them.
DEFAULT_COMFORT = 19.5
DEFAULT_SETBACK = 16.0
DEFAULT_FROST_HOLD = 12.0

DEFAULT_LEAD_TIME = timedelta(minutes=70)
# Floor heating responds slowly: warm up well ahead until the learner knows better.
DEFAULT_FLOOR_LEAD_TIME = timedelta(hours=3)


@dataclass(frozen=True)
class ScheduleWindow:
    """Comfort window: weekdays (Monday=0) it starts on, start inclusive, end exclusive.

    If end <= start the window runs past midnight into the next day.
    """

    days: frozenset[int]
    start: time
    end: time


@dataclass(frozen=True)
class RoomConfig:
    name: str
    comfort: float = DEFAULT_COMFORT
    setback: float = DEFAULT_SETBACK
    frost_hold: float = DEFAULT_FROST_HOLD
    schedule: tuple[ScheduleWindow, ...] = ()
    # Fixed pre-heat lead time: 60 min + 10 min burner latency (phase0 findings).
    lead_time: timedelta = DEFAULT_LEAD_TIME
    # No TRV: heated by always-open floor loops, so it only calls the boiler (long pre-heat).
    floor_heating: bool = False
    # No smart TRV (yet): radiators stay open, the room has a sensor. It calls the boiler like a
    # floor-heating room and, once at comfort, stops further calls so the house cannot overheat.
    open_radiators: bool = False
    trv_offset: float = 0.0  # added to the TRV sensor reading when no external sensor is used
    # Open-window detection: pause when temperature falls >= window_drop degC within
    # window_period; hold frost-hold for window_pause (clamped to 15-30 min).
    window_detection: bool = True
    window_drop: float = 0.8
    window_period: timedelta = timedelta(minutes=15)
    window_pause: timedelta = timedelta(minutes=20)
    # Correct the TRV setpoint for its sensor's difference with the room sensor, when the TRV
    # cannot take an external temperature (see compensation.py).
    compensate_trv: bool = True
    # Own demand hysteresis (degC) for a Room that needs another margin than the rest;
    # None follows EngineConfig.demand_hysteresis.
    demand_hysteresis: float | None = None
    # Stable id for entities and storage (the engine itself keys Rooms by name).
    id: str = field(default="", compare=False)


@dataclass(frozen=True)
class SensorConfig:
    """Staleness and push defaults from docs/research/phase0-findings.md."""

    external_stale_after: timedelta = timedelta(minutes=60)
    trv_stale_after: timedelta = timedelta(minutes=30)
    push_threshold: float = 0.3
    push_max_interval: timedelta = timedelta(minutes=15)


@dataclass(frozen=True)
class AlertConfig:
    """Alert thresholds from docs/research/phase0-findings.md, all configurable."""

    trv_offline_after: timedelta = timedelta(minutes=60)
    target_window: timedelta = timedelta(hours=3)
    outage_after_failures: int = 3
    sensor_stale_after: timedelta = timedelta(hours=2)
    battery_low_percent: float = 20.0


@dataclass(frozen=True)
class EngineConfig:
    rooms: tuple[RoomConfig, ...]
    boiler_low: float
    boiler_high: float
    sensors: SensorConfig = SensorConfig()
    # Boiler call policy (docs/research/phase0-findings.md, all configurable).
    boiler_debounce: timedelta = timedelta(minutes=5)
    boiler_backoff_base: timedelta = timedelta(minutes=5)
    boiler_backoff_max: timedelta = timedelta(minutes=30)
    # At most one write per this interval, whatever the cause (also guards the first write).
    boiler_min_interval: timedelta = timedelta(minutes=2)
    # The boiler thermostat reporting another setpoint than we set, this long after our write,
    # is a manual change: respected (no writes) for boiler_manual_hold.
    boiler_settle: timedelta = timedelta(minutes=10)
    boiler_manual_hold: timedelta = timedelta(hours=2)
    # A TRV reporting another setpoint than we wrote, this long after our write, is either
    # a lost write (retried, max 3 times) or a manual change (left alone until the target changes).
    trv_settle: timedelta = timedelta(minutes=10)
    # Demand only when a comfort-heating Room is colder than target by more than this (degC).
    demand_hysteresis: float = 0.3
    alerts: AlertConfig = AlertConfig()
    # Away longer than this drops rooms from setback to frost-hold.
    prolonged_absence: timedelta = timedelta(hours=48)


@dataclass(frozen=True)
class SensorReading:
    value: float
    at: datetime


@dataclass(frozen=True)
class Commands:
    """What the engine last issued, so it can debounce and avoid repeats."""

    trv_setpoints: Mapping[str, float] = field(default_factory=dict)
    boiler_setpoint: float | None = None
    boiler_changed_at: datetime | None = None
    # While set and in the future, a manual change on the boiler thermostat is respected.
    boiler_hold_until: datetime | None = None
    # TRV write bookkeeping: when we wrote, the value the TRV held just before, retries of
    # the current target, and Rooms whose TRV was changed by hand (value = target at that time).
    trv_written_at: Mapping[str, datetime] = field(default_factory=dict)
    trv_previous: Mapping[str, float] = field(default_factory=dict)
    trv_retries: Mapping[str, int] = field(default_factory=dict)
    trv_manual: Mapping[str, float] = field(default_factory=dict)
    external_temp_pushed: Mapping[str, float] = field(default_factory=dict)
    external_temp_pushed_at: Mapping[str, datetime] = field(default_factory=dict)
    window_paused_until: Mapping[str, datetime] = field(default_factory=dict)
    # Open-radiator Rooms that stopped every boiler call last cycle (kept until they cool off).
    open_radiators_capping: frozenset[str] = frozenset()


@dataclass(frozen=True)
class WriteResult:
    """Outcome of the adapter's latest boiler thermostat write attempt."""

    at: datetime
    status: Literal["ok", "rate_limited", "error"]
    retry_after: timedelta | None = None
    consecutive_failures: int = 0


@dataclass(frozen=True)
class Alert:
    code: str
    room: str | None = None
    message: str = ""


@dataclass(frozen=True)
class EngineInput:
    config: EngineConfig
    now: datetime
    anyone_home: bool
    learned: Mapping[str, timedelta]
    last_commands: Commands
    external_temps: Mapping[str, SensorReading] = field(default_factory=dict)
    trv_temps: Mapping[str, SensorReading] = field(default_factory=dict)
    last_write: WriteResult | None = None
    # Alert inputs: last TRV state report, low-battery flags, since when a Room is below target.
    trv_last_seen: Mapping[str, datetime] = field(default_factory=dict)
    battery_low: Mapping[str, bool] = field(default_factory=dict)
    unmet_since: Mapping[str, datetime] = field(default_factory=dict)
    boosts: Mapping[str, Boost] = field(default_factory=dict)
    manual_overrides: Mapping[str, ManualRoomOverride] = field(default_factory=dict)
    # Rooms whose assigned occupant entities are all away: no scheduled comfort heating there.
    absent_rooms: frozenset[str] = frozenset()
    # Rooms whose TRV has been switched off for a while despite correction attempts.
    trv_off: frozenset[str] = frozenset()
    # When the last tracked person left (None while someone is home).
    away_since: datetime | None = None
    # End of Vacation mode, or None when it is off. Kept set after it passes
    # until someone is home, so the schedule resumes before arrival.
    vacation_until: datetime | None = None
    # Setpoint the boiler thermostat currently reports (None when unknown), for re-asserting ours.
    boiler_observed: float | None = None
    # Setpoint each TRV currently reports (missing when unavailable), for lost-write detection.
    trv_observed: Mapping[str, float] = field(default_factory=dict)
    # Recent readings per Room (oldest first) for window detection: the TRV sensor where there
    # is one, else the Room temperature; and the external Room sensor on its own.
    temp_history: Mapping[str, tuple[SensorReading, ...]] = field(default_factory=dict)
    external_history: Mapping[str, tuple[SensorReading, ...]] = field(default_factory=dict)
    # Rooms whose radiator is cooling down after heating: their TRV sensor falls although the
    # Room does not, so window detection only trusts the external sensor there.
    cooling_rooms: frozenset[str] = frozenset()
    # Learned per Room (see insights.py): open-window drop, extra rise after a call ends, and
    # external-minus-TRV sensor offset. Missing while there is too little data.
    window_thresholds: Mapping[str, float] = field(default_factory=dict)
    coast: Mapping[str, float] = field(default_factory=dict)
    # Rooms whose call just ended and that are still warming from the radiator's stored heat:
    # they do not call again until the temperature has peaked (see CoastTracker).
    settling: frozenset[str] = frozenset()
    learned_offsets: Mapping[str, float] = field(default_factory=dict)
    # Rooms that have called for heat for a long time without warming up.
    stalled: frozenset[str] = frozenset()
    # Rooms whose TRV takes no external temperature (its setpoint may be corrected instead).
    trv_without_external: frozenset[str] = frozenset()


Reason = Literal[
    "boost", "window", "vacation", "away", "occupant_away", "manual", "floor_first", "satisfied", "pre_heat", "schedule", "setback"
]


@dataclass(frozen=True)
class Decision:
    trv_setpoints: Mapping[str, float]
    # None: nothing held yet and a first write is currently blocked (backoff); do not write.
    boiler_setpoint: float | None
    # Write boiler_setpoint even though unchanged (a manual hold ended and it still differs).
    boiler_reassert: bool = False
    # End of the manual hold on the boiler thermostat (carried back via Commands); no writes before it.
    boiler_hold_until: datetime | None = None
    # Rooms whose TRV setpoint must be re-written although unchanged (lost write).
    trv_rewrite: frozenset[str] = frozenset()
    # Rooms left alone after a manual TRV change (room -> target at that time), and retry counts.
    trv_manual: Mapping[str, float] = field(default_factory=dict)
    trv_retries: Mapping[str, int] = field(default_factory=dict)
    # Why each Room has its target (the precedence ladder's winning rung).
    reasons: Mapping[str, Reason] = field(default_factory=dict)
    alerts: tuple[Alert, ...] = ()
    room_temps: Mapping[str, float] = field(default_factory=dict)
    external_temp_pushes: Mapping[str, float] = field(default_factory=dict)
    window_paused_until: Mapping[str, datetime] = field(default_factory=dict)
    # Rooms whose TRV was set by hand, with the setpoint it holds (Room -> degC).
    hand_set: Mapping[str, float] = field(default_factory=dict)
    # Rooms whose unmet demand calls for the boiler (manual override not included).
    demand_rooms: tuple[str, ...] = ()
    # Open-radiator Rooms warm enough to stop every boiler call (carried back via Commands).
    open_radiators_capping: frozenset[str] = frozenset()
    # What to write to each TRV: its Room's target, corrected for TRVs that take no external
    # temperature. Empty means "the same as trv_setpoints".
    trv_writes: Mapping[str, float] = field(default_factory=dict)


ALL_DAYS = frozenset(range(7))
WORK_DAYS = frozenset({0, 2, 4})  # Mon/Wed/Fri

DEFAULT_LIVING_AREA_SCHEDULE = (ScheduleWindow(ALL_DAYS, time(6), time(23)),)
DEFAULT_WORK_SCHEDULE = (ScheduleWindow(WORK_DAYS, time(8), time(17)),)
