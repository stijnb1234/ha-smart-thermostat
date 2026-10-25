"""Setpoint correction for TRVs that cannot take an external room temperature.

Such a valve regulates on its own sensor next to the radiator, which reads warmer than the room.
Smart Heating writes the target plus that difference, so the room itself reaches the target.
"""

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


def make(clock, trv=21.0, room=19.0, written=None, compensate=True, can_take_external=False, observed=None, **room_kw):
    cfg = EngineConfig(
        rooms=(RoomConfig(name="office", comfort=19.5, schedule=ALWAYS, compensate_trv=compensate, **room_kw),),
        boiler_low=10.0,
        boiler_high=22.0,
    )
    cmds = Commands(
        trv_setpoints={} if written is None else {"office": written},
        trv_written_at={} if written is None else {"office": clock.now() - timedelta(minutes=30)},
    )
    return EngineInput(
        config=cfg,
        now=clock.now(),
        anyone_home=True,
        learned={},
        last_commands=cmds,
        trv_temps={"office": SensorReading(trv, clock.now())},
        external_temps={"office": SensorReading(room, clock.now())},
        trv_observed={} if observed is None else {"office": observed},
        trv_without_external=frozenset() if can_take_external else frozenset({"office"}),
    )


def test_valve_gets_the_target_plus_its_sensor_difference(clock):
    d = decide(make(clock, trv=21.0, room=19.0))
    assert d.trv_setpoints["office"] == 19.5  # the room's target is unchanged
    assert d.trv_writes["office"] == 21.5  # the valve aims 2 K higher, as it reads 2 K high


def test_written_value_is_rounded_to_half_degrees(clock):
    assert decide(make(clock, trv=20.3, room=19.0)).trv_writes["office"] == 21.0  # 19.5 + 1.3


def test_small_drift_keeps_the_last_written_value(clock):
    # 19.5 + 1.6 = 21.1 rounds to 21.0, but 21.5 was written: within the deadband, no new write.
    assert decide(make(clock, trv=20.6, room=19.0, written=21.5, observed=21.5)).trv_writes["office"] == 21.5


def test_larger_drift_writes_a_new_value(clock):
    assert decide(make(clock, trv=19.8, room=19.0, written=21.5, observed=21.5)).trv_writes["office"] == 20.5


def test_difference_is_capped(clock):
    assert decide(make(clock, trv=30.0, room=18.0)).trv_writes["office"] == 24.5  # at most +5 K


def test_no_correction_when_the_valve_takes_the_external_temperature(clock):
    assert decide(make(clock, can_take_external=True)).trv_writes["office"] == 19.5


def test_no_correction_when_switched_off_for_the_room(clock):
    assert decide(make(clock, compensate=False)).trv_writes["office"] == 19.5


def test_no_correction_without_a_fresh_room_sensor(clock):
    inp = make(clock)
    stale = {"office": SensorReading(19.0, clock.now() - timedelta(hours=2))}
    from dataclasses import replace

    assert decide(replace(inp, external_temps=stale)).trv_writes["office"] == 19.5


def test_corrected_write_that_landed_is_not_taken_for_a_hand_change(clock):
    d = decide(make(clock, trv=21.0, room=19.0, written=21.5, observed=21.5))
    assert d.trv_manual == {} and d.hand_set == {} and d.trv_rewrite == frozenset()


def test_hand_change_on_a_corrected_valve_is_shown_in_room_terms(clock):
    # Written 21.5 for a 19.5 target (+2 K); someone turned the valve to 24: that is 22 for the room.
    inp = make(clock, trv=21.0, room=19.0, written=21.5, observed=24.0)
    from dataclasses import replace

    inp = replace(inp, last_commands=replace(inp.last_commands, trv_previous={"office": 16.0}))
    d = decide(inp)
    assert d.hand_set == {"office": 22.0}
