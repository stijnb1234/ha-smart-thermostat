from datetime import datetime, time, timedelta, timezone

from custom_components.smart_heating.engine import (
    Commands,
    EngineConfig,
    EngineInput,
    RoomConfig,
    ScheduleWindow,
    SensorReading,
    decide,
    vacation_end,
)

ALL_DAYS = frozenset(range(7))


def make_input(clock, **overrides) -> EngineInput:
    room = RoomConfig(
        name="living",
        comfort=19.5,
        setback=16.0,
        frost_hold=12.0,
        schedule=(ScheduleWindow(ALL_DAYS, time(6), time(23)),),
    )
    defaults = dict(
        config=EngineConfig(rooms=(room,), easycontrol_low=10.0, easycontrol_high=22.0),
        now=clock.now(),
        anyone_home=True,
        learned={},
        last_commands=Commands(),
    )
    defaults.update(overrides)
    return EngineInput(**defaults)


def test_everyone_away_drops_room_to_setback_during_schedule(clock):
    clock.advance(hours=9)  # 12:00, inside the window
    away_since = clock.now() - timedelta(hours=1)

    decision = decide(make_input(clock, anyone_home=False, away_since=away_since))

    assert decision.trv_setpoints == {"living": 16.0}


def test_someone_home_follows_schedule(clock):
    clock.advance(hours=9)

    decision = decide(make_input(clock))

    assert decision.trv_setpoints == {"living": 19.5}


def test_prolonged_absence_holds_frost(clock):
    clock.advance(hours=9)
    away_since = clock.now() - timedelta(hours=49)

    decision = decide(make_input(clock, anyone_home=False, away_since=away_since))

    assert decision.trv_setpoints == {"living": 12.0}


def test_prolonged_absence_threshold_is_configurable(clock):
    clock.advance(hours=9)
    base = make_input(clock)
    config = EngineConfig(
        rooms=base.config.rooms,
        easycontrol_low=10.0,
        easycontrol_high=22.0,
        prolonged_absence=timedelta(hours=6),
    )
    away_since = clock.now() - timedelta(hours=7)

    decision = decide(
        make_input(clock, config=config, anyone_home=False, away_since=away_since)
    )

    assert decision.trv_setpoints == {"living": 12.0}


def test_return_home_resumes_schedule(clock):
    clock.advance(hours=9)

    away = decide(
        make_input(clock, anyone_home=False, away_since=clock.now() - timedelta(hours=60))
    )
    home = decide(make_input(clock, anyone_home=True, away_since=None))

    assert away.trv_setpoints == {"living": 12.0}
    assert home.trv_setpoints == {"living": 19.5}


def test_vacation_holds_frost_even_when_someone_is_home(clock):
    clock.advance(hours=9)
    until = clock.now() + timedelta(days=3)

    decision = decide(make_input(clock, vacation_until=until))

    assert decision.trv_setpoints == {"living": 12.0}


def test_vacation_over_resumes_schedule_even_before_arrival(clock):
    clock.advance(hours=9)
    until = clock.now() - timedelta(minutes=1)

    decision = decide(
        make_input(
            clock,
            anyone_home=False,
            away_since=clock.now() - timedelta(days=5),
            vacation_until=until,
        )
    )

    assert decision.trv_setpoints == {"living": 19.5}


def test_vacation_ends_at_start_of_arrival_day():
    start = datetime(2026, 1, 12, 15, 30, tzinfo=timezone.utc)

    assert vacation_end(start, days=7) == datetime(2026, 1, 19, 0, 0, tzinfo=timezone.utc)


def test_vacation_keeps_boiler_call_low(clock):
    clock.advance(hours=9)
    until = clock.now() + timedelta(days=3)

    decision = decide(
        make_input(clock, vacation_until=until, trv_temps={"living": SensorReading(13.0, clock.now())})
    )

    assert decision.easycontrol_setpoint == 10.0
