"""Boiler call: demand aggregation, debounce and backoff for the EasyControl setpoint (ADR-0002)."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Mapping

from .models import EPSILON, EngineConfig, EngineInput, WriteResult

# Observed vs held setpoints closer than this count as equal (thermostat resolution).
_DRIFT_TOLERANCE = 0.05


def demand_rooms(
    config: EngineConfig,
    trv_setpoints: Mapping[str, float],
    room_temps: Mapping[str, float],
    hand_set: Mapping[str, float] | None = None,
) -> tuple[str, ...]:
    """Rooms heating to comfort that are colder than target by more than the hysteresis.

    Rooms at setback or frost-hold never call for heat: they are allowed to
    drift down and the boiler should not fire for a few tenths of a degree.
    A Room whose TRV was set by hand (`hand_set`: Room -> that setpoint) calls for heat
    when the hand-set value is above its setback, as that shows someone wants it warm.
    """
    hand_set = hand_set or {}
    calling = []
    for room in config.rooms:
        if room.name not in room_temps:
            continue
        if room.name in hand_set:
            wanted = hand_set[room.name]
            wants = wanted > room.setback + EPSILON
        else:
            wanted = trv_setpoints[room.name]
            wants = wanted >= room.comfort - EPSILON
        if wants and room_temps[room.name] < wanted - config.demand_hysteresis:
            calling.append(room.name)
    return tuple(calling)


def has_demand(
    config: EngineConfig,
    trv_setpoints: Mapping[str, float],
    room_temps: Mapping[str, float],
) -> bool:
    """True if any Room has unmet demand (see demand_rooms)."""
    return bool(demand_rooms(config, trv_setpoints, room_temps))


def backoff_delay(config: EngineConfig, result: WriteResult) -> timedelta:
    """How long after a failed write the next attempt is held back."""
    return _backoff(config, result)


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


def easycontrol_setpoint(
    inp: EngineInput, demand: bool
) -> tuple[float | None, bool, datetime | None]:
    """(setpoint to hold, whether to re-write it though unchanged, manual hold end).

    The setpoint is None when nothing is held yet and a first write is blocked
    (backoff or minimum interval), so the adapter stays quiet. While a change is
    blocked or a manual hold runs, the currently held setpoint is returned, so the
    adapter (which writes only on change) stays quiet too.

    A setpoint on the EasyControl that differs from what we set, `easycontrol_settle`
    after our write, is a manual change: hold off writing for `easycontrol_manual_hold`.
    When the hold ends and it still differs from the desired one, write the desired one.
    """
    cfg, now = inp.config, inp.now
    desired = cfg.easycontrol_high if demand else cfg.easycontrol_low
    held = inp.last_commands.easycontrol_setpoint
    hold = inp.last_commands.easycontrol_hold_until
    observed = inp.easycontrol_observed
    if held is None:
        return (None, False, None) if _blocked(inp) else (desired, False, None)
    if hold is not None:
        if now < hold:
            return held, False, hold
        if observed is not None and abs(observed - desired) >= _DRIFT_TOLERANCE:
            # Hold over and still not what we want: write, or wait for the block to pass.
            if _blocked(inp):
                return held, False, hold
            return desired, held == desired, None
    changed_at = inp.last_commands.easycontrol_changed_at
    if (
        observed is not None
        and abs(observed - held) >= _DRIFT_TOLERANCE
        and changed_at is not None
        and now - changed_at >= cfg.easycontrol_settle
    ):
        return held, False, now + cfg.easycontrol_manual_hold
    if held == desired:
        return held, False, None
    return (held, False, None) if _blocked(inp) else (desired, False, None)
