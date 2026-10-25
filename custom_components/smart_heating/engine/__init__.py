"""Pure decision engine. No Home Assistant imports allowed in this package."""

from .alerts import AlertChanges, AlertNotifier, track_unmet
from .engine import decide
from .models import (
    DEFAULT_COMFORT,
    DEFAULT_FLOOR_LEAD_TIME,
    DEFAULT_FROST_HOLD,
    DEFAULT_LEAD_TIME,
    DEFAULT_LIVING_AREA_SCHEDULE,
    DEFAULT_SETBACK,
    DEFAULT_WORK_SCHEDULE,
    EPSILON,
    Alert,
    AlertConfig,
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
from .overrides import (
    Boost,
    ManualRoomOverride,
    timed_requests_from_dict,
    timed_requests_to_dict,
)
from .presence import vacation_release
from .schedule import in_window, lead_time_for, wants_comfort
from .sensors import select_temperature, select_window_temperature
from .state import commands_from_dict, commands_to_dict

__all__ = [
    "DEFAULT_COMFORT",
    "DEFAULT_FLOOR_LEAD_TIME",
    "DEFAULT_FROST_HOLD",
    "DEFAULT_LEAD_TIME",
    "DEFAULT_LIVING_AREA_SCHEDULE",
    "DEFAULT_SETBACK",
    "DEFAULT_WORK_SCHEDULE",
    "EPSILON",
    "Alert",
    "AlertChanges",
    "AlertConfig",
    "AlertNotifier",
    "Boost",
    "Commands",
    "Decision",
    "EngineConfig",
    "EngineInput",
    "ManualRoomOverride",
    "RoomConfig",
    "ScheduleWindow",
    "SensorConfig",
    "SensorReading",
    "WriteResult",
    "commands_from_dict",
    "commands_to_dict",
    "decide",
    "in_window",
    "lead_time_for",
    "select_temperature",
    "select_window_temperature",
    "timed_requests_from_dict",
    "timed_requests_to_dict",
    "track_unmet",
    "vacation_release",
    "wants_comfort",
]
