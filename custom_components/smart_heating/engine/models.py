"""Input and output types of the decision engine (the single test seam)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from typing import Literal, Mapping

from .overrides import Boost, ManualRoomOverride

# Float comparison tolerance for thresholds.
EPSILON = 1e-9

# Default targets (spec: comfort 19.5, setback 16, frost-hold 12). The single place for them.
DEFAULT_COMFORT = 19.5
DEFAULT_SETBACK = 16.0
DEFAULT_FROST_HOLD = 12.0

DEFAULT_LEAD_TIME = timedelta(minutes=70)


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
    trv_offset: float = 0.0  # added to the TRV sensor reading when no external sensor is used
    # Open-window detection: pause when temperature falls >= window_drop degC within
    # window_period; hold frost-hold for window_pause (clamped to 15-30 min).
    window_detection: bool = True
    window_drop: float = 1.5
    window_period: timedelta = timedelta(minutes=10)
    window_pause: timedelta = timedelta(minutes=20)


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
    easycontrol_low: float
    easycontrol_high: float
    sensors: SensorConfig = SensorConfig()
    # Boiler call policy (docs/research/phase0-findings.md, all configurable).
    easycontrol_debounce: timedelta = timedelta(minutes=5)
    easycontrol_backoff_base: timedelta = timedelta(minutes=5)
    easycontrol_backoff_max: timedelta = timedelta(minutes=30)
    # At most one write per this interval, whatever the cause (also guards the first write).
    easycontrol_min_interval: timedelta = timedelta(minutes=2)
    # The EasyControl reporting another setpoint than we set, this long after our write,
    # is a manual change: respected (no writes) for easycontrol_manual_hold.
    easycontrol_settle: timedelta = timedelta(minutes=10)
    easycontrol_manual_hold: timedelta = timedelta(hours=2)
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
    easycontrol_setpoint: float | None = None
    easycontrol_changed_at: datetime | None = None
    # While set and in the future, a manual change on the EasyControl is respected.
    easycontrol_hold_until: datetime | None = None
    # TRV write bookkeeping: when we wrote, the value the TRV held just before, retries of
    # the current target, and Rooms whose TRV was changed by hand (value = target at that time).
    trv_written_at: Mapping[str, datetime] = field(default_factory=dict)
    trv_previous: Mapping[str, float] = field(default_factory=dict)
    trv_retries: Mapping[str, int] = field(default_factory=dict)
    trv_manual: Mapping[str, float] = field(default_factory=dict)
    external_temp_pushed: Mapping[str, float] = field(default_factory=dict)
    external_temp_pushed_at: Mapping[str, datetime] = field(default_factory=dict)
    window_paused_until: Mapping[str, datetime] = field(default_factory=dict)


@dataclass(frozen=True)
class WriteResult:
    """Outcome of the adapter's latest EasyControl write attempt."""

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
    # When the last tracked person left (None while someone is home).
    away_since: datetime | None = None
    # End of Vacation mode, or None when it is off. Kept set after it passes
    # until someone is home, so the schedule resumes before arrival.
    vacation_until: datetime | None = None
    # Setpoint the EasyControl currently reports (None when unknown), for re-asserting ours.
    easycontrol_observed: float | None = None
    # Setpoint each TRV currently reports (missing when unavailable), for lost-write detection.
    trv_observed: Mapping[str, float] = field(default_factory=dict)
    # Recent Room temperature readings per Room (oldest first) for window detection.
    temp_history: Mapping[str, tuple[SensorReading, ...]] = field(default_factory=dict)


Reason = Literal["boost", "window", "vacation", "away", "pre_heat", "schedule", "setback"]


@dataclass(frozen=True)
class Decision:
    trv_setpoints: Mapping[str, float]
    # None: nothing held yet and a first write is currently blocked (backoff); do not write.
    easycontrol_setpoint: float | None
    # Write easycontrol_setpoint even though unchanged (a manual hold ended and it still differs).
    easycontrol_reassert: bool = False
    # End of the manual hold on the EasyControl (carried back via Commands); no writes before it.
    easycontrol_hold_until: datetime | None = None
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
    # Rooms whose unmet demand calls for the boiler (manual override not included).
    demand_rooms: tuple[str, ...] = ()


ALL_DAYS = frozenset(range(7))
WORK_DAYS = frozenset({0, 2, 4})  # Mon/Wed/Fri

DEFAULT_LIVING_AREA_SCHEDULE = (ScheduleWindow(ALL_DAYS, time(6), time(23)),)
DEFAULT_WORK_SCHEDULE = (ScheduleWindow(WORK_DAYS, time(8), time(17)),)
