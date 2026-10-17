"""Boiler call: demand aggregation, debounce and backoff for the EasyControl setpoint (ADR-0002)."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Mapping

from .models import EPSILON, EngineConfig, EngineInput, WriteResult

# Observed vs held setpoints closer than this count as equal (thermostat resolution).
_DRIFT_TOLERANCE = 0.05


def has_demand(
    config: EngineConfig,
    trv_setpoints: Mapping[str, float],
    room_temps: Mapping[str, float],
) -> bool:
    """True if a Room heating to comfort is colder than its target by more than the hysteresis.

    Rooms at setback or frost-hold never call for heat: they are allowed to
    drift down and the boiler should not fire for a few tenths of a degree.
    """
    return any(
        room.name in room_temps
        and trv_setpoints[room.name] >= room.comfort - EPSILON
        and room_temps[room.name] < trv_setpoints[room.name] - config.demand_hysteresis
        for room in config.rooms
    )


def _backoff(config: EngineConfig, result: WriteResult) -> timedelta:
    if result.retry_after is not None:
        return result.retry_after
    doublings = max(result.consecutive_failures - 1, 0)
    return min(config.easycontrol_backoff_base * 2**doublings, config.easycontrol_backoff_max)


def _blocked(inp: EngineInput) -> bool:
    """Whether a write now would break the minimum interval, debounce or backoff."""
    cfg, now = inp.config, inp.now
    changed_at: datetime | None = inp.last_commands.easycontrol_changed_at
    result = inp.last_write
    attempts = [t for t in (changed_at, result.at if result else None) if t is not None]
    if attempts and now - max(attempts) < cfg.easycontrol_min_interval:
        return True
    if changed_at is not None and now - changed_at < cfg.easycontrol_debounce:
        return True
    if result is not None and result.status != "ok":
        return now - result.at < _backoff(cfg, result)
    return False


def _drifted(inp: EngineInput, held: float) -> bool:
    """The EasyControl reports something else than we last set, for long enough to re-assert."""
    observed = inp.easycontrol_observed
    if observed is None or abs(observed - held) < _DRIFT_TOLERANCE:
        return False
    changed_at = inp.last_commands.easycontrol_changed_at
    return changed_at is None or inp.now - changed_at >= inp.config.easycontrol_reassert_after


def easycontrol_setpoint(inp: EngineInput, demand: bool) -> tuple[float | None, bool]:
    """(setpoint to hold, whether to re-write it even though unchanged).

    The setpoint is None when nothing is held yet and a first write is blocked
    (backoff or minimum interval), so the adapter stays quiet. While a change is
    blocked the currently held setpoint is returned, so the adapter (which writes
    only on change) stays quiet too.
    """
    desired = inp.config.easycontrol_high if demand else inp.config.easycontrol_low
    held = inp.last_commands.easycontrol_setpoint
    if held is None:
        return (None, False) if _blocked(inp) else (desired, False)
    if held == desired:
        if _drifted(inp, held) and not _blocked(inp):
            return desired, True
        return held, False
    return (held, False) if _blocked(inp) else (desired, False)
