"""Pure decision engine. No Home Assistant imports allowed in this package."""

from .alerts import AlertChanges, AlertNotifier, track_unmet
from .engine import decide, in_window, lead_time_for, wants_comfort
from .sensors import select_temperature
from .presence import vacation_end
from .state import commands_from_dict, commands_to_dict
from .models import (
    AlertConfig,
    DEFAULT_COMFORT,
    DEFAULT_FROST_HOLD,
    DEFAULT_FLOOR_LEAD_TIME,
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

from .overrides import (
    Boost,
    ManualRoomOverride,
    timed_requests_from_dict,
    timed_requests_to_dict,
)

__all__ = [
    "commands_from_dict",
    "commands_to_dict",
    "Boost",
    "ManualRoomOverride",
    "timed_requests_from_dict",
    "timed_requests_to_dict",
    "DEFAULT_COMFORT",
    "DEFAULT_FROST_HOLD",
    "DEFAULT_FLOOR_LEAD_TIME",
    "DEFAULT_LEAD_TIME",
    "DEFAULT_SETBACK",
    "EPSILON",
    "lead_time_for",
    "in_window",
    "wants_comfort",
    "select_temperature",
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
