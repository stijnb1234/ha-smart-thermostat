"""Boiler call: demand aggregation, debounce and backoff for the EasyControl setpoint (ADR-0002)."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Mapping

from .models import EngineConfig, EngineInput, WriteResult


def has_demand(
    config: EngineConfig,
    trv_setpoints: Mapping[str, float],
    room_temps: Mapping[str, float],
) -> bool:
    """True if any Room with a reading is colder than its target."""
    return any(
        room.name in room_temps and room_temps[room.name] < trv_setpoints[room.name]
        for room in config.rooms
    )


def _backoff(config: EngineConfig, result: WriteResult) -> timedelta:
    if result.retry_after is not None:
        return result.retry_after
    doublings = max(result.consecutive_failures - 1, 0)
    return min(config.easycontrol_backoff_base * 2**doublings, config.easycontrol_backoff_max)


def _blocked(inp: EngineInput) -> bool:
    cfg, now = inp.config, inp.now
    changed_at: datetime | None = inp.last_commands.easycontrol_changed_at
    if changed_at is not None and now - changed_at < cfg.easycontrol_debounce:
        return True
    result = inp.last_write
    if result is not None and result.status != "ok":
        return now - result.at < _backoff(cfg, result)
    return False


def easycontrol_setpoint(inp: EngineInput, demand: bool) -> float:
    """Setpoint the EasyControl should hold now.

    Returns the currently held setpoint while a change is debounced or backing off,
    so the adapter (which writes only on change) stays quiet.
    """
    desired = inp.config.easycontrol_high if demand else inp.config.easycontrol_low
    held = inp.last_commands.easycontrol_setpoint
    if held is None or held == desired:
        return desired if held is None else held
    return held if _blocked(inp) else desired
