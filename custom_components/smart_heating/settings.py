"""Pure mapping from config entry options to engine configuration. No Home Assistant imports.

Defaults come from the engine's own dataclasses, so they live in one place.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any, Mapping

from .const import (
    CONF_BACKOFF_BASE_MINUTES,
    CONF_BACKOFF_MAX_MINUTES,
    CONF_BATTERY_LOW_PERCENT,
    CONF_BOOST_MINUTES,
    CONF_DEBOUNCE_MINUTES,
    CONF_DEMAND_HYSTERESIS,
    CONF_EASYCONTROL_MANUAL_HOLD_MINUTES,
    CONF_EASYCONTROL_SETTLE_MINUTES,
    CONF_TRV_SETTLE_MINUTES,
    CONF_EASYCONTROL_HIGH,
    CONF_EASYCONTROL_LOW,
    CONF_MANUAL_OVERRIDE_MINUTES,
    CONF_OUTAGE_FAILURES,
    CONF_SENSOR_STALE_HOURS,
    CONF_TARGET_WINDOW_HOURS,
    CONF_TRV_OFFLINE_MINUTES,
    DEFAULT_BOOST_MINUTES,
    DEFAULT_EASYCONTROL_HIGH,
    DEFAULT_EASYCONTROL_LOW,
    DEFAULT_MANUAL_OVERRIDE_MINUTES,
)
from .engine import AlertConfig, EngineConfig, RoomConfig


def _minutes(options: Mapping[str, Any], key: str, default: timedelta) -> timedelta:
    value = options.get(key)
    return default if value is None else timedelta(minutes=float(value))


def _hours(options: Mapping[str, Any], key: str, default: timedelta) -> timedelta:
    value = options.get(key)
    return default if value is None else timedelta(hours=float(value))


def build_engine_config(rooms: tuple[RoomConfig, ...], options: Mapping[str, Any]) -> EngineConfig:
    base, alerts = EngineConfig(rooms=(), easycontrol_low=0, easycontrol_high=0), AlertConfig()
    return EngineConfig(
        rooms=rooms,
        easycontrol_low=float(options.get(CONF_EASYCONTROL_LOW, DEFAULT_EASYCONTROL_LOW)),
        easycontrol_high=float(options.get(CONF_EASYCONTROL_HIGH, DEFAULT_EASYCONTROL_HIGH)),
        easycontrol_debounce=_minutes(options, CONF_DEBOUNCE_MINUTES, base.easycontrol_debounce),
        easycontrol_backoff_base=_minutes(
            options, CONF_BACKOFF_BASE_MINUTES, base.easycontrol_backoff_base
        ),
        easycontrol_backoff_max=_minutes(
            options, CONF_BACKOFF_MAX_MINUTES, base.easycontrol_backoff_max
        ),
        easycontrol_settle=_minutes(
            options, CONF_EASYCONTROL_SETTLE_MINUTES, base.easycontrol_settle
        ),
        easycontrol_manual_hold=_minutes(
            options, CONF_EASYCONTROL_MANUAL_HOLD_MINUTES, base.easycontrol_manual_hold
        ),
        trv_settle=_minutes(options, CONF_TRV_SETTLE_MINUTES, base.trv_settle),
        demand_hysteresis=float(options.get(CONF_DEMAND_HYSTERESIS, base.demand_hysteresis)),
        alerts=AlertConfig(
            trv_offline_after=_minutes(options, CONF_TRV_OFFLINE_MINUTES, alerts.trv_offline_after),
            target_window=_hours(options, CONF_TARGET_WINDOW_HOURS, alerts.target_window),
            outage_after_failures=int(options.get(CONF_OUTAGE_FAILURES, alerts.outage_after_failures)),
            sensor_stale_after=_hours(options, CONF_SENSOR_STALE_HOURS, alerts.sensor_stale_after),
            battery_low_percent=float(
                options.get(CONF_BATTERY_LOW_PERCENT, alerts.battery_low_percent)
            ),
        ),
    )


def boost_duration(options: Mapping[str, Any]) -> timedelta:
    return timedelta(minutes=float(options.get(CONF_BOOST_MINUTES, DEFAULT_BOOST_MINUTES)))


def manual_override_duration(options: Mapping[str, Any]) -> timedelta:
    return timedelta(
        minutes=float(options.get(CONF_MANUAL_OVERRIDE_MINUTES, DEFAULT_MANUAL_OVERRIDE_MINUTES))
    )
