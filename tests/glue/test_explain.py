from datetime import datetime, time, timedelta, timezone

from custom_components.smart_heating.engine import (
    Boost,
    Commands,
    EngineConfig,
    EngineInput,
    RoomConfig,
    ScheduleWindow,
    SensorReading,
    decide,
)
from custom_components.smart_heating.explain import explain

UTC = timezone.utc
ROOM = RoomConfig(
    name="work",
    comfort=20.0,
    setback=16.0,
    frost_hold=12.0,
    schedule=(ScheduleWindow(frozenset({0}), time(8), time(17)),),  # Mondays
)
MON_10 = datetime(2026, 1, 12, 10, 0, tzinfo=UTC)  # a Monday


def run(now, temp=18.0, room=ROOM, **kw):
    inp = EngineInput(
        config=EngineConfig(rooms=(room,), easycontrol_low=10, easycontrol_high=22),
        now=now,
        anyone_home=kw.pop("anyone_home", True),
        trv_temps={room.name: SensorReading(temp, now)},
        learned={},
        last_commands=Commands(),
        **kw,
    )
    return explain(room, inp, decide(inp))


def test_in_window_is_schedule_and_next_change_is_window_end():
    e = run(MON_10)
    assert (e.reason, e.target) == ("schedule", 20.0)
    assert (e.next_change_at, e.next_change_target) == (
        datetime(2026, 1, 12, 17, 0, tzinfo=UTC),
        16.0,
    )


def test_outside_window_is_setback_next_change_is_preheat_start():
    e = run(datetime(2026, 1, 12, 3, 0, tzinfo=UTC))
    assert e.reason == "setback"
    # default lead time 70 min before 08:00
    assert e.next_change_at == datetime(2026, 1, 12, 6, 50, tzinfo=UTC)
    assert e.next_change_target == 20.0


def test_preheat_reason_in_lead_time():
    e = run(datetime(2026, 1, 12, 7, 30, tzinfo=UTC))
    assert (e.reason, e.target) == ("pre_heat", 20.0)


def test_boost_reason_and_next_change_is_boost_end():
    boost = {"work": Boost(MON_10 - timedelta(minutes=10), timedelta(minutes=60))}
    e = run(MON_10, boosts=boost)
    assert e.reason == "boost"
    assert e.next_change_at == MON_10 + timedelta(minutes=50)


def test_away_has_no_next_change():
    e = run(MON_10, anyone_home=False, away_since=MON_10 - timedelta(hours=1))
    assert (e.reason, e.target, e.next_change_at) == ("away", 16.0, None)


def test_vacation_reason_next_change_is_vacation_end():
    until = datetime(2026, 1, 19, 0, 0, tzinfo=UTC)
    e = run(MON_10, anyone_home=False, vacation_until=until)
    assert (e.reason, e.target, e.next_change_at) == ("vacation", 12.0, until)


def test_window_open_pause():
    e = run(
        MON_10,
        temp=17.0,
        temp_history={
            "work": (
                SensorReading(19.0, MON_10 - timedelta(minutes=5)),
                SensorReading(17.0, MON_10),
            )
        },
    )
    assert (e.reason, e.target) == ("window", 12.0)
    assert e.next_change_at == MON_10 + timedelta(minutes=20)


def test_room_without_schedule_has_no_next_change():
    e = run(MON_10, room=RoomConfig(name="work"))
    assert e.reason == "setback" and e.next_change_at is None
