"""Input and output types of the decision engine (the single test seam)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Mapping


@dataclass(frozen=True)
class RoomConfig:
    name: str
    comfort: float = 19.5
    setback: float = 16.0
    frost_hold: float = 12.0


@dataclass(frozen=True)
class EngineConfig:
    rooms: tuple[RoomConfig, ...]
    easycontrol_low: float
    easycontrol_high: float


@dataclass(frozen=True)
class Commands:
    """What the engine last issued, so it can debounce and avoid repeats."""

    trv_setpoints: Mapping[str, float] = field(default_factory=dict)
    easycontrol_setpoint: float | None = None
    easycontrol_changed_at: datetime | None = None


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


@dataclass(frozen=True)
class Decision:
    trv_setpoints: Mapping[str, float]
    easycontrol_setpoint: float
    alerts: tuple[Alert, ...] = ()
