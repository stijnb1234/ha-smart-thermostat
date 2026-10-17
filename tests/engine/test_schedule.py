from datetime import time

from custom_components.smart_heating.engine import (
    Commands,
    EngineConfig,
    EngineInput,
    RoomConfig,
    ScheduleWindow,
    decide,
)

ALL_DAYS = frozenset(range(7))
MON_WED_FRI = frozenset({0, 2, 4})


def make_input(clock, rooms, **overrides) -> EngineInput:
    defaults = dict(
        config=EngineConfig(rooms=tuple(rooms), easycontrol_low=10.0, easycontrol_high=22.0),
        now=clock.now(),
        anyone_home=True,
        learned={},
        last_commands=Commands(),
    )
    defaults.update(overrides)
    return EngineInput(**defaults)


def living():
    return RoomConfig(
        name="living", schedule=(ScheduleWindow(ALL_DAYS, time(6), time(23)),)
    )


def working():
    return RoomConfig(
        name="working", schedule=(ScheduleWindow(MON_WED_FRI, time(8), time(17)),)
    )


def bedroom():
    return RoomConfig(
        name="bedroom", schedule=(ScheduleWindow(MON_WED_FRI, time(8), time(17)),)
    )


def setpoint(clock, room):
    return decide(make_input(clock, [room])).trv_setpoints[room.name]


def test_defaults_are_comfort_19_5_and_setback_16():
    room = RoomConfig(name="x")
    assert (room.comfort, room.setback) == (19.5, 16.0)


def test_living_area_is_comfort_inside_window_and_setback_outside(clock):
    # fake clock starts Monday 2026-01-12 03:00
    assert setpoint(clock, living()) == 16.0
    clock.advance(hours=3)  # 06:00 inclusive start
    assert setpoint(clock, living()) == 19.5
    clock.advance(hours=16, minutes=59)  # 22:59
    assert setpoint(clock, living()) == 19.5
    clock.advance(minutes=1)  # 23:00 exclusive end
    assert setpoint(clock, living()) == 16.0


def test_working_room_heats_only_on_configured_days_and_hours(clock):
    clock.advance(hours=9)  # Monday 12:00
    assert setpoint(clock, working()) == 19.5
    clock.advance(hours=5)  # Monday 17:00
    assert setpoint(clock, working()) == 16.0
    clock.advance(hours=-5, days=1)  # Tuesday 12:00
    assert setpoint(clock, working()) == 16.0
    clock.advance(days=1)  # Wednesday 12:00
    assert setpoint(clock, working()) == 19.5


def test_bedroom_follows_work_hours(clock):
    clock.advance(hours=9)  # Monday 12:00
    assert setpoint(clock, bedroom()) == 19.5
    clock.advance(days=1)  # Tuesday
    assert setpoint(clock, bedroom()) == 16.0


def test_per_room_comfort_and_setback_are_used(clock):
    room = RoomConfig(
        name="r", comfort=21.0, setback=15.0,
        schedule=(ScheduleWindow(ALL_DAYS, time(6), time(23)),),
    )
    assert setpoint(clock, room) == 15.0
    clock.advance(hours=9)
    assert setpoint(clock, room) == 21.0


def test_window_crossing_midnight(clock):
    room = RoomConfig(
        name="r", schedule=(ScheduleWindow(ALL_DAYS, time(22), time(2)),)
    )
    assert setpoint(clock, room) == 16.0  # 03:00, window ended 02:00
    clock.advance(hours=-2)  # 01:00
    assert setpoint(clock, room) == 19.5


def test_spec_default_schedules(clock):
    from custom_components.smart_heating.engine import (
        DEFAULT_LIVING_AREA_SCHEDULE,
        DEFAULT_WORK_SCHEDULE,
    )

    liv = RoomConfig(name="l", schedule=DEFAULT_LIVING_AREA_SCHEDULE)
    wrk = RoomConfig(name="w", schedule=DEFAULT_WORK_SCHEDULE)
    assert setpoint(clock, liv) == 16.0
    clock.advance(hours=9)
    assert setpoint(clock, liv) == 19.5
    assert setpoint(clock, wrk) == 19.5
    clock.advance(days=1)
    assert setpoint(clock, wrk) == 16.0


def test_schedule_uses_the_wall_clock_of_now_not_utc():
    from datetime import datetime, time, timedelta, timezone

    from custom_components.smart_heating.engine import RoomConfig, ScheduleWindow, in_window

    room = RoomConfig(name="x", schedule=(ScheduleWindow(frozenset(range(7)), time(8), time(17)),))
    local = timezone(timedelta(hours=2))
    # 07:30 local is 05:30 UTC: outside the window either way; 08:30 local is 06:30 UTC.
    assert in_window(room, datetime(2026, 10, 17, 8, 30, tzinfo=local))
    assert not in_window(room, datetime(2026, 10, 17, 8, 30, tzinfo=local).astimezone(timezone.utc))
