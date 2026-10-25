from custom_components.smart_heating.engine import (
    Commands,
    EngineConfig,
    EngineInput,
    RoomConfig,
    decide,
)


def make_input(clock, **overrides) -> EngineInput:
    config = EngineConfig(
        rooms=(RoomConfig(name="bedroom", comfort=19.5, setback=16.0, frost_hold=12.0),),
        boiler_low=10.0,
        boiler_high=22.0,
    )
    defaults = {
        "config": config,
        "now": clock.now(),
        "anyone_home": True,
        "learned": {},
        "last_commands": Commands(),
    }
    defaults.update(overrides)
    return EngineInput(**defaults)


def test_room_without_demand_is_set_back(clock):
    decision = decide(make_input(clock))

    assert decision.trv_setpoints == {"bedroom": 16.0}


def test_no_demand_anywhere_keeps_boiler_call_low(clock):
    decision = decide(make_input(clock))

    assert decision.boiler_setpoint == 10.0
    assert decision.alerts == ()


def test_setback_holds_as_time_advances(clock):
    clock.advance(hours=5)

    decision = decide(make_input(clock))

    assert decision.trv_setpoints == {"bedroom": 16.0}
