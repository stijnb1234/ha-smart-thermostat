"""Input and output types of the decision engine (the single test seam)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from typing import Literal, Mapping

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
    comfort: float = 19.5
    setback: float = 16.0
    frost_hold: float = 12.0
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
    push_threshold: float = 0.3
    push_max_interval: timedelta = timedelta(minutes=15)


@dataclass(frozen=True)
class AlertConfig:
    """Alert thresholds from docs/research/phase0-findings.md, all configurable."""

    trv_offline_after: timedelta = timedelta(minutes=60)
    target_window: timedelta = timedelta(hours=3)
    outage_after_failures: int = 3


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
    alerts: AlertConfig = AlertConfig()


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
    room_temps: Mapping[str, float]
    learned: Mapping[str, object]
    last_commands: Commands
    external_temps: Mapping[str, SensorReading] = field(default_factory=dict)
    trv_temps: Mapping[str, SensorReading] = field(default_factory=dict)
    last_write: WriteResult | None = None
    # Alert inputs: last TRV state report, low-battery flags, since when a Room is below target.
    trv_last_seen: Mapping[str, datetime] = field(default_factory=dict)
    battery_low: Mapping[str, bool] = field(default_factory=dict)
    unmet_since: Mapping[str, datetime] = field(default_factory=dict)

    # Recent Room temperature readings per Room (oldest first) for window detection.
    temp_history: Mapping[str, tuple[SensorReading, ...]] = field(default_factory=dict)


@dataclass(frozen=True)
class Decision:
    trv_setpoints: Mapping[str, float]
    easycontrol_setpoint: float
    alerts: tuple[Alert, ...] = ()
    room_temps: Mapping[str, float] = field(default_factory=dict)
    external_temp_pushes: Mapping[str, float] = field(default_factory=dict)
    window_paused_until: Mapping[str, datetime] = field(default_factory=dict)


ALL_DAYS = frozenset(range(7))
WORK_DAYS = frozenset({0, 2, 4})  # Mon/Wed/Fri

DEFAULT_LIVING_AREA_SCHEDULE = (ScheduleWindow(ALL_DAYS, time(6), time(23)),)
DEFAULT_WORK_SCHEDULE = (ScheduleWindow(WORK_DAYS, time(8), time(17)),)
