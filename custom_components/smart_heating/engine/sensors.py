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
    learned_offsets: Mapping[str, float] | None = None,
) -> tuple[float | None, bool]:
    """Return (room temperature, whether it came from the external sensor).

    A fresh external sensor wins; otherwise a fresh TRV reading plus the Room's
    offset (the learned external-minus-TRV offset when none is configured);
    otherwise None (stale readings are not trusted).
    """
    ext = external.get(room.name)
    if ext is not None and now - ext.at < cfg.external_stale_after:
        return ext.value, True
    reading = trv.get(room.name)
    if reading is not None and now - reading.at < cfg.trv_stale_after:
        offset = room.trv_offset or (learned_offsets or {}).get(room.name, 0.0)
        return reading.value + offset, False
    return None, False


def select_window_temperature(
    room: RoomConfig,
    external: Mapping[str, SensorReading],
    trv: Mapping[str, SensorReading],
    now: datetime,
    cfg: SensorConfig,
) -> float | None:
    """Temperature for open-window detection: the TRV sensor first, as it usually sits by the
    window and reacts sooner; otherwise the Room temperature. Only changes matter, so no offset."""
    reading = trv.get(room.name)
    if reading is not None and now - reading.at < cfg.trv_stale_after:
        return reading.value
    return select_temperature(room, external, trv, now, cfg)[0]
