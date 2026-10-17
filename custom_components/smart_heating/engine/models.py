"""Input and output types of the decision engine (the single test seam)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from typing import Literal, Mapping


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


@dataclass(frozen=True)
class EngineConfig:
    rooms: tuple[RoomConfig, ...]
    easycontrol_low: float
    easycontrol_high: float
    # Boiler call policy (docs/research/phase0-findings.md, all configurable).
    easycontrol_debounce: timedelta = timedelta(minutes=5)
    easycontrol_backoff_base: timedelta = timedelta(minutes=5)
    easycontrol_backoff_max: timedelta = timedelta(minutes=30)


@dataclass(frozen=True)
class Commands:
    """What the engine last issued, so it can debounce and avoid repeats."""

    trv_setpoints: Mapping[str, float] = field(default_factory=dict)
    easycontrol_setpoint: float | None = None
    easycontrol_changed_at: datetime | None = None


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
    last_write: WriteResult | None = None


@dataclass(frozen=True)
class Decision:
    trv_setpoints: Mapping[str, float]
    easycontrol_setpoint: float
    alerts: tuple[Alert, ...] = ()


ALL_DAYS = frozenset(range(7))
WORK_DAYS = frozenset({0, 2, 4})  # Mon/Wed/Fri

DEFAULT_LIVING_AREA_SCHEDULE = (ScheduleWindow(ALL_DAYS, time(6), time(23)),)
DEFAULT_WORK_SCHEDULE = (ScheduleWindow(WORK_DAYS, time(8), time(17)),)
