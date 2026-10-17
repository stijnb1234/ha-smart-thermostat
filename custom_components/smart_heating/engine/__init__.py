"""Pure decision engine. No Home Assistant imports allowed in this package."""

from .alerts import AlertChanges, AlertNotifier, track_unmet
from .engine import decide, lead_time_for
from .models import (
    AlertConfig,
    DEFAULT_LEAD_TIME,
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

__all__ = [
    "DEFAULT_LEAD_TIME",
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
]
