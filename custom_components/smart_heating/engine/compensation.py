"""Setpoint correction for TRVs that cannot take an external room temperature.

Such a valve regulates on its own sensor next to the radiator, which reads warmer than the
room. The value written is the Room's target plus that difference (rounded to half degrees,
capped), so the room itself reaches the target. A deadband keeps the last written value while
the difference wanders a little, so the valve is not rewritten every few minutes.
"""

from __future__ import annotations

from collections.abc import Mapping

from .models import EngineInput

MAX_CORRECTION = 5.0
DEADBAND = 0.75  # keep the last write while target + difference stays this close to it
MIN_SETPOINT, MAX_SETPOINT = 5.0, 30.0


def _half(value: float) -> float:
    return round(value * 2) / 2


def trv_writes(inp: EngineInput, targets: Mapping[str, float]) -> dict[str, float]:
    """What to write to each TRV for its Room's target."""
    cfg = inp.config.sensors
    writes = dict(targets)
    for room in inp.config.rooms:
        name = room.name
        if not room.compensate_trv or name not in inp.trv_without_external or name not in targets:
            continue
        trv, ext = inp.trv_temps.get(name), inp.external_temps.get(name)
        if (
            trv is None
            or ext is None
            or inp.now - trv.at >= cfg.trv_stale_after
            or inp.now - ext.at >= cfg.external_stale_after
        ):
            continue
        correction = min(max(trv.value - ext.value, -MAX_CORRECTION), MAX_CORRECTION)
        wanted = targets[name] + correction
        previous = inp.last_commands.trv_setpoints.get(name)
        if previous is not None and abs(wanted - previous) < DEADBAND:
            writes[name] = previous
        else:
            writes[name] = min(max(_half(wanted), MIN_SETPOINT), MAX_SETPOINT)
    return writes
