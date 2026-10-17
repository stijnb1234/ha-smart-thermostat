"""Room temperature selection: the one rule shared by the engine and the controller's history."""

from __future__ import annotations

from datetime import datetime
from typing import Mapping

from .models import RoomConfig, SensorConfig, SensorReading


def select_temperature(
    room: RoomConfig,
    external: Mapping[str, SensorReading],
    trv: Mapping[str, SensorReading],
    now: datetime,
    cfg: SensorConfig,
) -> tuple[float | None, bool]:
    """Return (room temperature, whether it came from the external sensor).

    A fresh external sensor wins; otherwise a fresh TRV reading plus the Room's
    offset; otherwise None (stale readings are not trusted).
    """
    ext = external.get(room.name)
    if ext is not None and now - ext.at < cfg.external_stale_after:
        return ext.value, True
    reading = trv.get(room.name)
    if reading is not None and now - reading.at < cfg.trv_stale_after:
        return reading.value + room.trv_offset, False
    return None, False
