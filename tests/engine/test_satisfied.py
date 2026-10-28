from dataclasses import replace
from datetime import time, timedelta

from custom_components.smart_heating.engine import (
    Commands,
    EngineConfig,
    EngineInput,
    RoomConfig,
    ScheduleWindow,
    SensorReading,
    decide,
)

ALWAYS = (ScheduleWindow(frozenset(range(7)), time(0), time(23, 59)),)


def _input(clock, room_temp, *, room=None, last_setpoint=None, age=timedelta(0)):
    room = room or RoomConfig(name="study", comfort=20.0, setback=16.0, frost_hold=12.0, schedule=ALWAYS)
    now = clock.now()
    return EngineInput(
        config=EngineConfig(rooms=(room,), boiler_low=10.0, boiler_high=22.0),
        now=now,
        anyone_home=True,
        learned={},
        last_commands=Commands(trv_setpoints={} if last_setpoint is None else {room.name: last_setpoint}),
        external_temps={room.name: SensorReading(room_temp, now - age)},
        # The valve's own sensor reads colder than the room, so left alone it would open.
        trv_temps={room.name: SensorReading(17.0, now)},
    )


def test_room_at_target_closes_its_valve(clock):
    clock.advance(hours=12)

    d = decide(_input(clock, 20.0))

    assert (d.trv_setpoints["study"], d.reasons["study"]) == (12.0, "satisfied")


def test_closed_room_still_reports_its_real_target(clock):
    clock.advance(hours=12)

    d = decide(_input(clock, 20.0))

    assert d.satisfied_targets == {"study": 20.0}


def test_room_below_target_keeps_heating(clock):
    clock.advance(hours=12)

    d = decide(_input(clock, 19.9))

    assert (d.trv_setpoints["study"], d.reasons["study"]) == (20.0, "schedule")


def test_closed_valve_reopens_only_once_room_cooled_past_hysteresis(clock):
    clock.advance(hours=12)

    still_shut = decide(_input(clock, 19.8, last_setpoint=12.0))
    reopened = decide(_input(clock, 19.6, last_setpoint=12.0))

    assert (still_shut.trv_setpoints["study"], still_shut.reasons["study"]) == (12.0, "satisfied")
    assert (reopened.trv_setpoints["study"], reopened.reasons["study"]) == (20.0, "schedule")


def test_setback_room_above_setback_closes_its_valve(clock):
    room = RoomConfig(name="study", comfort=20.0, setback=16.0, frost_hold=12.0)  # no schedule

    d = decide(_input(clock, 17.5, room=room))

    assert (d.trv_setpoints["study"], d.reasons["study"]) == (12.0, "satisfied")


def test_stale_sensor_is_not_trusted_to_close_the_valve(clock):
    clock.advance(hours=12)

    d = decide(_input(clock, 21.0, age=timedelta(hours=2)))

    assert d.reasons["study"] == "schedule"


def test_room_already_at_frost_hold_is_left_as_it_is(clock):
    room = RoomConfig(name="study", comfort=20.0, setback=12.0, frost_hold=12.0)

    d = decide(_input(clock, 15.0, room=room))

    assert (d.trv_setpoints["study"], d.reasons["study"]) == (12.0, "setback")


def test_open_radiator_room_is_not_closed(clock):
    clock.advance(hours=12)
    room = RoomConfig(
        name="study", comfort=20.0, setback=16.0, frost_hold=12.0, schedule=ALWAYS, open_radiators=True
    )

    d = decide(_input(clock, 21.0, room=room))

    assert d.reasons["study"] == "schedule"


def test_satisfied_room_does_not_call_for_heat(clock):
    clock.advance(hours=12)
    inp = _input(clock, 20.5)

    d = decide(inp)

    assert d.demand_rooms == ()
    assert d.boiler_setpoint == 10.0
    assert decide(replace(inp, external_temps={})).reasons["study"] == "schedule"  # no sensor: unchanged
