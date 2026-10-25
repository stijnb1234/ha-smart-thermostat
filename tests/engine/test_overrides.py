from datetime import timedelta

from custom_components.smart_heating.engine import (
    Boost,
    Commands,
    EngineConfig,
    EngineInput,
    ManualRoomOverride,
    RoomConfig,
    SensorReading,
    decide,
)

LOW, HIGH = 10.0, 22.0


def make_input(clock, temps=None, **kw) -> EngineInput:
    config = EngineConfig(
        rooms=(RoomConfig(name="bedroom", comfort=19.5, setback=16.0),),
        boiler_low=LOW,
        boiler_high=HIGH,
    )
    temps = temps or {"bedroom": 18.0}
    return EngineInput(
        config=config,
        now=clock.now(),
        trv_temps={n: SensorReading(v, clock.now()) for n, v in temps.items()},
        learned={},
        last_commands=Commands(),
        **{"anyone_home": True, **kw},
    )


def test_boost_raises_room_to_comfort_and_calls_for_heat(clock):
    boost = {"bedroom": Boost(start=clock.now(), duration=timedelta(minutes=60))}

    d = decide(make_input(clock, boosts=boost))

    assert d.trv_setpoints["bedroom"] == 19.5
    assert d.boiler_setpoint == HIGH


def test_boost_expires_after_duration(clock):
    boost = {"bedroom": Boost(start=clock.now(), duration=timedelta(minutes=60))}
    clock.advance(minutes=60)

    d = decide(make_input(clock, boosts=boost))

    assert d.trv_setpoints["bedroom"] == 16.0
    assert d.boiler_setpoint == LOW


def test_boost_still_active_just_before_expiry(clock):
    boost = {"bedroom": Boost(start=clock.now(), duration=timedelta(minutes=60))}
    clock.advance(minutes=59)

    d = decide(make_input(clock, boosts=boost))

    assert d.trv_setpoints["bedroom"] == 19.5


def test_boost_beats_away(clock):
    boost = {"bedroom": Boost(start=clock.now(), duration=timedelta(minutes=30))}

    d = decide(make_input(clock, boosts=boost, anyone_home=False))

    assert d.trv_setpoints["bedroom"] == 19.5


def test_boost_for_other_room_does_not_affect_this_one(clock):
    boost = {"office": Boost(start=clock.now(), duration=timedelta(minutes=30))}

    d = decide(make_input(clock, boosts=boost))

    assert d.trv_setpoints["bedroom"] == 16.0


def test_manual_room_override_raises_boiler_call_without_room_demand(clock):
    # Bedroom is warm enough; the override is for a dumb-TRV room not in the config.
    manual = {"hallway": ManualRoomOverride(start=clock.now(), duration=timedelta(hours=2))}

    d = decide(make_input(clock, temps={"bedroom": 18.0}, manual_overrides=manual))

    assert d.boiler_setpoint == HIGH
    assert "hallway" not in d.trv_setpoints


def test_manual_room_override_expires_and_boiler_call_returns_low(clock):
    manual = {"hallway": ManualRoomOverride(start=clock.now(), duration=timedelta(hours=2))}
    clock.advance(hours=2)

    d = decide(make_input(clock, manual_overrides=manual))

    assert d.boiler_setpoint == LOW
