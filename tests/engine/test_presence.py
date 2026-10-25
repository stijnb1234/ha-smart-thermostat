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

ALL_DAYS = frozenset(range(7))


def make_input(clock, **overrides) -> EngineInput:
    room = RoomConfig(
        name="living",
        comfort=19.5,
        setback=16.0,
        frost_hold=12.0,
        schedule=(ScheduleWindow(ALL_DAYS, time(6), time(23)),),
    )
    defaults = {
        "config": EngineConfig(rooms=(room,), boiler_low=10.0, boiler_high=22.0),
        "now": clock.now(),
        "anyone_home": True,
        "learned": {},
        "last_commands": Commands(),
    }
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
        boiler_low=10.0,
        boiler_high=22.0,
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


def test_vacation_releases_each_room_its_lead_time_before_the_return(clock):
    clock.advance(hours=9)  # 12:00, inside the comfort window
    back = clock.now() + timedelta(hours=2)
    learned = {"living": timedelta(hours=2, minutes=30)}

    decision = decide(make_input(clock, vacation_until=back, learned=learned))

    # Warming up from frost-hold takes 2.5 h: the room leaves Vacation now, warm on return.
    assert decision.trv_setpoints == {"living": 19.5}
    assert decision.reasons["living"] == "schedule"


def test_vacation_holds_frost_until_the_release_moment(clock):
    clock.advance(hours=9)
    back = clock.now() + timedelta(hours=3)
    learned = {"living": timedelta(hours=2, minutes=30)}

    decision = decide(make_input(clock, vacation_until=back, learned=learned))

    assert decision.trv_setpoints == {"living": 12.0}


def test_vacation_keeps_boiler_call_low(clock):
    clock.advance(hours=9)
    until = clock.now() + timedelta(days=3)

    decision = decide(
        make_input(clock, vacation_until=until, trv_temps={"living": SensorReading(13.0, clock.now())})
    )

    assert decision.boiler_setpoint == 10.0


def test_absent_occupant_skips_schedule_but_boost_wins(clock):
    from custom_components.smart_heating.engine import Boost

    clock.advance(hours=9)  # inside the window
    d = decide(make_input(clock, absent_rooms=frozenset({"living"})))
    assert (d.trv_setpoints["living"], d.reasons["living"]) == (16.0, "occupant_away")
    boost = {"living": Boost(clock.now(), timedelta(hours=1))}
    d = decide(make_input(clock, absent_rooms=frozenset({"living"}), boosts=boost))
    assert d.reasons["living"] == "boost"


def test_absent_occupant_outside_schedule_stays_plain_setback(clock):
    d = decide(make_input(clock, absent_rooms=frozenset({"living"})))  # midnight
    assert d.reasons["living"] == "setback"


def test_absent_occupant_blocks_early_comfort(clock):
    clock.advance(hours=5, minutes=30)  # in the pre-heat lead before the 06:00 window
    assert decide(make_input(clock)).trv_setpoints["living"] == 19.5
    assert decide(make_input(clock, absent_rooms=frozenset({"living"}))).reasons["living"] == "occupant_away"
