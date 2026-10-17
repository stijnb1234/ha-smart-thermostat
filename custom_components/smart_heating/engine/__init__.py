"""Pure decision engine. No Home Assistant imports allowed in this package."""

from .alerts import AlertChanges, AlertNotifier, track_unmet
from .engine import decide, lead_time_for
from .presence import vacation_end
from .models import (
    AlertConfig,
    DEFAULT_COMFORT,
    DEFAULT_FROST_HOLD,
    DEFAULT_LEAD_TIME,
    DEFAULT_SETBACK,
    EPSILON,
    DEFAULT_LIVING_AREA_SCHEDULE,
    DEFAULT_WORK_SCHEDULE,
    Alert,
    Commands,
    Decision,
    EngineConfig,
    EngineInput,
    RoomConfig,
    ScheduleWindow,
    SensorConfig,
    SensorReading,
    WriteResult,
)

from .overrides import Boost, ManualRoomOverride

__all__ = [
    "Boost",
    "ManualRoomOverride",
    "DEFAULT_COMFORT",
    "DEFAULT_FROST_HOLD",
    "DEFAULT_LEAD_TIME",
    "DEFAULT_SETBACK",
    "EPSILON",
    "lead_time_for",
    "DEFAULT_LIVING_AREA_SCHEDULE",
    "DEFAULT_WORK_SCHEDULE",
    "Alert",
    "AlertChanges",
    "AlertConfig",
    "AlertNotifier",
    "track_unmet",
    "Commands",
    "Decision",
    "EngineConfig",
    "EngineInput",
    "RoomConfig",
    "ScheduleWindow",
    "SensorConfig",
    "SensorReading",
    "WriteResult",
    "decide",
    "vacation_end",
]
