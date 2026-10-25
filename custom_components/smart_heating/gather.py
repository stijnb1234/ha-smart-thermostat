"""Pure helpers for gathering engine inputs from raw HA state values. No HA imports."""

from __future__ import annotations

from datetime import datetime, timedelta

from .engine import SensorReading


def parse_number(text: object) -> float | None:
    """A state string as float, or None for unknown/unavailable/garbage."""
    try:
        value = float(text)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return value if value == value else None  # reject NaN


def update_history(
    history: tuple[SensorReading, ...],
    reading: SensorReading,
    now: datetime,
    keep: timedelta,
) -> tuple[SensorReading, ...]:
    """Append a reading and drop those older than `keep`."""
    return tuple(r for r in (*history, reading) if now - r.at <= keep)


def battery_is_low(state: object, threshold_percent: float) -> bool:
    value = parse_number(state)
    return value is not None and value < threshold_percent
