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
    assert cfg.easycontrol_debounce == EngineConfig(rooms=(), easycontrol_low=0, easycontrol_high=0).easycontrol_debounce
    assert (cfg.easycontrol_low, cfg.easycontrol_high) == (15.0, 22.0)
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

    assert cfg.easycontrol_debounce == timedelta(minutes=10)
    assert cfg.easycontrol_backoff_base == timedelta(minutes=2)
    assert cfg.easycontrol_backoff_max == timedelta(minutes=60)
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
