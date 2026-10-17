from datetime import timedelta

from custom_components.smart_heating.engine import (
    Commands,
    EngineConfig,
    EngineInput,
    RoomConfig,
    SensorReading,
    WriteResult,
    decide,
)

LOW, HIGH = 10.0, 22.0


def make_input(clock, temps=None, commands=None, last_write=None) -> EngineInput:
    config = EngineConfig(
        rooms=(
            RoomConfig(name="bedroom", comfort=19.5, setback=16.0),
            RoomConfig(name="office", comfort=19.5, setback=16.0),
        ),
        easycontrol_low=LOW,
        easycontrol_high=HIGH,
    )
    return EngineInput(
        config=config,
        now=clock.now(),
        anyone_home=True,
        room_temps={},
        trv_temps={
            name: SensorReading(value=value, at=clock.now())
            for name, value in (temps or {"bedroom": 17.0, "office": 17.0}).items()
        },
        learned={},
        last_commands=commands or Commands(),
        last_write=last_write,
    )


def held(clock, setpoint, ago_minutes):
    return Commands(
        easycontrol_setpoint=setpoint,
        easycontrol_changed_at=clock.now() - timedelta(minutes=ago_minutes),
    )


def test_no_demand_calls_low(clock):
    # Both rooms at or above their setback target.
    d = decide(make_input(clock, temps={"bedroom": 16.0, "office": 18.0}))

    assert d.easycontrol_setpoint == LOW


def test_demand_in_one_room_raises_setpoint(clock):
    d = decide(make_input(clock, temps={"bedroom": 17.0, "office": 15.0}))

    assert d.easycontrol_setpoint == HIGH


def test_room_without_reading_creates_no_demand(clock):
    d = decide(make_input(clock, temps={"bedroom": 16.5}))

    assert d.easycontrol_setpoint == LOW


def test_change_within_debounce_window_is_held_back(clock):
    cmds = held(clock, LOW, ago_minutes=2)

    d = decide(make_input(clock, temps={"office": 15.0}, commands=cmds))

    assert d.easycontrol_setpoint == LOW


def test_change_allowed_after_debounce_window(clock):
    cmds = held(clock, LOW, ago_minutes=5)

    d = decide(make_input(clock, temps={"office": 15.0}, commands=cmds))

    assert d.easycontrol_setpoint == HIGH


def test_lowering_is_debounced_too(clock):
    cmds = held(clock, HIGH, ago_minutes=1)

    d = decide(make_input(clock, temps={"office": 20.0, "bedroom": 20.0}, commands=cmds))

    assert d.easycontrol_setpoint == HIGH


def test_rate_limited_write_backs_off_five_minutes_then_retries(clock):
    cmds = held(clock, LOW, ago_minutes=60)
    result = WriteResult(at=clock.now(), status="rate_limited", consecutive_failures=1)
    temps = {"office": 15.0}

    assert decide(make_input(clock, temps, cmds, result)).easycontrol_setpoint == LOW
    clock.advance(minutes=4)
    assert decide(make_input(clock, temps, cmds, result)).easycontrol_setpoint == LOW
    clock.advance(minutes=1)
    assert decide(make_input(clock, temps, cmds, result)).easycontrol_setpoint == HIGH


def test_backoff_doubles_and_caps_at_thirty_minutes(clock):
    cmds = held(clock, LOW, ago_minutes=600)
    temps = {"office": 15.0}

    def setpoint_after(failures, minutes):
        result = WriteResult(
            at=clock.now() - timedelta(minutes=minutes),
            status="rate_limited",
            consecutive_failures=failures,
        )
        return decide(make_input(clock, temps, cmds, result)).easycontrol_setpoint

    assert setpoint_after(2, 9) == LOW
    assert setpoint_after(2, 10) == HIGH
    assert setpoint_after(3, 19) == LOW
    assert setpoint_after(3, 20) == HIGH
    assert setpoint_after(9, 29) == LOW
    assert setpoint_after(9, 30) == HIGH


def test_retry_after_overrides_computed_backoff(clock):
    cmds = held(clock, LOW, ago_minutes=600)
    result = WriteResult(
        at=clock.now() - timedelta(minutes=6),
        status="rate_limited",
        retry_after=timedelta(minutes=15),
        consecutive_failures=1,
    )

    d = decide(make_input(clock, {"office": 15.0}, cmds, result))

    assert d.easycontrol_setpoint == LOW


def test_other_write_errors_use_same_backoff(clock):
    cmds = held(clock, LOW, ago_minutes=600)
    result = WriteResult(at=clock.now(), status="error", consecutive_failures=1)

    d = decide(make_input(clock, {"office": 15.0}, cmds, result))

    assert d.easycontrol_setpoint == LOW


def test_successful_write_result_does_not_delay(clock):
    cmds = held(clock, LOW, ago_minutes=600)
    result = WriteResult(at=clock.now(), status="ok")

    d = decide(make_input(clock, {"office": 15.0}, cmds, result))

    assert d.easycontrol_setpoint == HIGH
