from datetime import UTC, timedelta

from custom_components.smart_heating.engine import (
    Commands,
    EngineConfig,
    EngineInput,
    RoomConfig,
    SensorReading,
    decide,
)


def make_input(clock, room=None, **overrides) -> EngineInput:
    room = room or RoomConfig(name="living", trv_offset=-1.5)
    defaults = {
        "config": EngineConfig(rooms=(room,), boiler_low=10.0, boiler_high=22.0),
        "now": clock.now(),
        "anyone_home": True,
        "learned": {},
        "last_commands": Commands(),
    }
    defaults.update(overrides)
    return EngineInput(**defaults)


def reading(clock, value, age_min=0):
    return SensorReading(value, clock.now() - timedelta(minutes=age_min))


def test_fresh_external_sensor_is_preferred_over_trv(clock):
    decision = decide(
        make_input(
            clock,
            external_temps={"living": reading(clock, 19.0)},
            trv_temps={"living": reading(clock, 22.0)},
        )
    )

    assert decision.room_temps == {"living": 19.0}


def test_trv_sensor_plus_offset_used_without_external_sensor(clock):
    decision = decide(make_input(clock, trv_temps={"living": reading(clock, 22.0)}))

    assert decision.room_temps == {"living": 20.5}


def test_stale_external_reading_falls_back_to_trv_plus_offset(clock):
    decision = decide(
        make_input(
            clock,
            external_temps={"living": reading(clock, 19.0, age_min=61)},
            trv_temps={"living": reading(clock, 22.0)},
        )
    )

    assert decision.room_temps == {"living": 20.5}


def test_external_reading_just_inside_staleness_limit_is_used(clock):
    decision = decide(
        make_input(
            clock,
            external_temps={"living": reading(clock, 19.0, age_min=59)},
            trv_temps={"living": reading(clock, 22.0)},
        )
    )

    assert decision.room_temps == {"living": 19.0}


def test_room_without_any_fresh_reading_has_no_temperature(clock):
    decision = decide(make_input(clock))

    assert decision.room_temps == {}


def test_first_external_temperature_is_pushed(clock):
    decision = decide(make_input(clock, external_temps={"living": reading(clock, 19.0)}))

    assert decision.external_temp_pushes == {"living": 19.0}


def test_unchanged_external_temperature_is_not_pushed_again(clock):
    pushed = Commands(
        external_temp_pushed={"living": 19.0},
        external_temp_pushed_at={"living": clock.now() - timedelta(minutes=5)},
    )

    decision = decide(
        make_input(clock, external_temps={"living": reading(clock, 19.2)}, last_commands=pushed)
    )

    assert decision.external_temp_pushes == {}


def test_change_of_threshold_size_is_pushed(clock):
    pushed = Commands(
        external_temp_pushed={"living": 19.0},
        external_temp_pushed_at={"living": clock.now() - timedelta(minutes=5)},
    )

    decision = decide(
        make_input(clock, external_temps={"living": reading(clock, 19.3)}, last_commands=pushed)
    )

    assert decision.external_temp_pushes == {"living": 19.3}


def test_unchanged_temperature_is_repushed_after_max_interval(clock):
    pushed = Commands(
        external_temp_pushed={"living": 19.0},
        external_temp_pushed_at={"living": clock.now() - timedelta(minutes=15)},
    )

    decision = decide(
        make_input(clock, external_temps={"living": reading(clock, 19.0)}, last_commands=pushed)
    )

    assert decision.external_temp_pushes == {"living": 19.0}


def test_nothing_pushed_when_external_reading_is_stale(clock):
    decision = decide(
        make_input(clock, external_temps={"living": reading(clock, 19.0, age_min=90)})
    )

    assert decision.external_temp_pushes == {}


def test_trv_reading_older_than_thirty_minutes_is_stale(clock):
    fresh = decide(make_input(clock, trv_temps={"living": reading(clock, 20.0, age_min=29)}))
    stale = decide(make_input(clock, trv_temps={"living": reading(clock, 20.0, age_min=31)}))

    assert fresh.room_temps == {"living": 18.5}
    assert stale.room_temps == {}


def test_stale_trv_reading_creates_no_boiler_demand(clock):
    d = decide(make_input(clock, trv_temps={"living": reading(clock, 5.0, age_min=45)}))

    assert d.boiler_setpoint == 10.0


def test_window_temperature_prefers_the_trv_sensor_without_offset():
    from datetime import datetime

    from custom_components.smart_heating.engine import RoomConfig, SensorConfig, SensorReading
    from custom_components.smart_heating.engine.sensors import select_window_temperature

    now = datetime(2026, 1, 12, 12, 0, tzinfo=UTC)
    room = RoomConfig(name="bed", trv_offset=-1.0)
    ext, trv = {"bed": SensorReading(19.0, now)}, {"bed": SensorReading(21.0, now)}
    assert select_window_temperature(room, ext, trv, now, SensorConfig()) == 21.0
    assert select_window_temperature(room, ext, {}, now, SensorConfig()) == 19.0
