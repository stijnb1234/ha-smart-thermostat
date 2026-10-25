from datetime import timedelta

from custom_components.smart_heating.engine import AlertConfig, EngineConfig
from custom_components.smart_heating.settings import (
    boost_duration,
    build_engine_config,
    manual_override_duration,
)


def test_empty_options_give_engine_defaults():
    cfg = build_engine_config((), {})

    assert cfg.alerts == AlertConfig()
    assert cfg.boiler_debounce == EngineConfig(rooms=(), boiler_low=0, boiler_high=0).boiler_debounce
    assert (cfg.boiler_low, cfg.boiler_high) == (15.0, 22.0)
    assert boost_duration({}) == timedelta(minutes=60)
    assert manual_override_duration({}) == timedelta(hours=2)


def test_options_override_boiler_and_alert_policy():
    cfg = build_engine_config(
        (),
        {
            "debounce_minutes": 10,
            "backoff_base_minutes": 2,
            "backoff_max_minutes": 60,
            "demand_hysteresis": 0.5,
            "trv_offline_minutes": 90,
            "target_window_hours": 4,
            "outage_after_failures": 5,
            "sensor_stale_hours": 3,
            "battery_low_percent": 30,
        },
    )

    assert cfg.boiler_debounce == timedelta(minutes=10)
    assert cfg.boiler_backoff_base == timedelta(minutes=2)
    assert cfg.boiler_backoff_max == timedelta(minutes=60)
    assert cfg.demand_hysteresis == 0.5
    assert cfg.alerts == AlertConfig(
        trv_offline_after=timedelta(minutes=90),
        target_window=timedelta(hours=4),
        outage_after_failures=5,
        sensor_stale_after=timedelta(hours=3),
        battery_low_percent=30.0,
    )


def test_timed_request_durations_are_configurable():
    assert boost_duration({"boost_minutes": 90}) == timedelta(minutes=90)
    assert manual_override_duration({"manual_override_minutes": 30}) == timedelta(minutes=30)


def test_manual_change_options():
    cfg = build_engine_config(
        (),
        {"trv_settle_minutes": 15, "boiler_settle_minutes": 20, "boiler_manual_hold_minutes": 180},
    )

    assert cfg.trv_settle == timedelta(minutes=15)
    assert cfg.boiler_settle == timedelta(minutes=20)
    assert cfg.boiler_manual_hold == timedelta(hours=3)
    default = build_engine_config((), {})
    assert (default.trv_settle, default.boiler_manual_hold) == (timedelta(minutes=10), timedelta(hours=2))
