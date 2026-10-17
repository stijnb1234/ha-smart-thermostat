from datetime import time, timedelta

from custom_components.smart_heating.engine import RoomConfig, ScheduleWindow
from tests.engine.test_schedule import ALL_DAYS, setpoint


def morning_room(**kw):
    return RoomConfig(
        name="r", schedule=(ScheduleWindow(ALL_DAYS, time(6), time(23)),), **kw
    )


def test_default_lead_time_is_60_min_plus_10_min_burner_latency():
    assert RoomConfig(name="x").lead_time == timedelta(minutes=70)


def test_room_goes_to_comfort_one_lead_time_before_window_start(clock):
    room = morning_room()  # clock starts Monday 03:00; window starts 06:00
    clock.advance(hours=1, minutes=49)  # 04:49
    assert setpoint(clock, room) == 16.0
    clock.advance(minutes=1)  # 04:50 = 06:00 - 70 min
    assert setpoint(clock, room) == 19.5


def test_lead_time_is_configurable_per_room(clock):
    room = morning_room(lead_time=timedelta(minutes=30))
    clock.advance(hours=2, minutes=29)  # 05:29
    assert setpoint(clock, room) == 16.0
    clock.advance(minutes=1)  # 05:30
    assert setpoint(clock, room) == 19.5


def test_pre_heat_does_not_extend_window_end(clock):
    room = morning_room()
    clock.advance(hours=19, minutes=59)  # 22:59
    assert setpoint(clock, room) == 19.5
    clock.advance(minutes=1)  # 23:00, end is exclusive
    assert setpoint(clock, room) == 16.0


def test_pre_heat_crosses_midnight_to_next_day_window(clock):
    room = RoomConfig(
        name="r",
        schedule=(ScheduleWindow(frozenset({1}), time(0, 30), time(8)),),
        lead_time=timedelta(hours=1),
    )  # Tuesday 00:30 window; Monday 23:30 pre-heat start
    clock.advance(hours=20, minutes=29)  # Monday 23:29
    assert setpoint(clock, room) == 16.0
    clock.advance(minutes=1)
    assert setpoint(clock, room) == 19.5


def test_lead_time_for_prefers_learned_value_over_fixed():
    from custom_components.smart_heating.engine import lead_time_for

    room = morning_room()
    assert lead_time_for(room, {}) == timedelta(minutes=70)
    assert lead_time_for(room, {"r": timedelta(minutes=20)}) == timedelta(minutes=20)
