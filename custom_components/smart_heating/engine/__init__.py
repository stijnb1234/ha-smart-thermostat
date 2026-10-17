"""Pure decision engine. No Home Assistant imports allowed in this package."""

from .engine import decide
from .models import (
    DEFAULT_LIVING_AREA_SCHEDULE,
    DEFAULT_WORK_SCHEDULE,
    Alert,
    Commands,
    Decision,
    EngineConfig,
    EngineInput,
    RoomConfig,
    ScheduleWindow,
    WriteResult,
)

__all__ = [
    "DEFAULT_LIVING_AREA_SCHEDULE",
    "DEFAULT_WORK_SCHEDULE",
    "Alert",
    "Commands",
    "Decision",
    "EngineConfig",
    "EngineInput",
    "RoomConfig",
    "ScheduleWindow",
    "WriteResult",
    "decide",
]
