from datetime import time, timedelta

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

ALWAYS = (ScheduleWindow(frozenset(range(7)), time(0), time(23, 59)),)


def test_boost_beats_window_pause_beats_vacation_and_away_beats_schedule(clock):
    clock.advance(hours=12)
    now = clock.now()
    rooms = tuple(
        RoomConfig(name=n, comfort=20.0, setback=16.0, frost_hold=12.0, schedule=ALWAYS)
        for n in ("boosted", "falling", "steady")
    )
    config = EngineConfig(rooms=rooms, easycontrol_low=10.0, easycontrol_high=22.0)

    def history(drop):
        start = 19.0
        return (
            SensorReading(start, now - timedelta(minutes=3)),
            SensorReading(start - drop, now),
        )

    def run(**kw):
        return decide(
            EngineInput(
                config=config,
                now=now,
                learned={},
                last_commands=Commands(),
                trv_temps={n: SensorReading(19.0, now) for n in ("boosted", "falling", "steady")},
                temp_history={
                    "boosted": history(2.0),
                    "falling": history(2.0),
                    "steady": history(0.0),
                },
                boosts={"boosted": Boost(start=now, duration=timedelta(minutes=60))},
                **kw,
            )
        )

    away_d = run(anyone_home=False, away_since=now - timedelta(hours=1))
    away = away_d.trv_setpoints
    assert away_d.reasons == {"boosted": "boost", "falling": "window", "steady": "away"}
    assert away["boosted"] == 20.0  # Boost beats window pause and Away
    assert away["falling"] == 12.0  # window pause beats Away (setback)
    assert away["steady"] == 16.0  # Away beats schedule (comfort)

    vacation_d = run(anyone_home=True, vacation_until=now + timedelta(days=3))
    vacation = vacation_d.trv_setpoints
    assert vacation_d.reasons["steady"] == "vacation"
    assert vacation["boosted"] == 20.0
    assert vacation["steady"] == 12.0  # Vacation beats schedule
    away_only = run(anyone_home=True)
    assert away_only.trv_setpoints["steady"] == 20.0  # schedule when nobody overrides
    assert away_only.reasons["steady"] == "schedule"


def test_floor_preheat_keeps_idle_radiators_shut_and_calls_boiler(clock):
    from datetime import time

    from custom_components.smart_heating.engine import (
        Commands, EngineConfig, EngineInput, RoomConfig, ScheduleWindow, SensorReading, decide,
    )

    clock.advance(hours=4)  # 07:00, two hours before the 09:00 window
    window = (ScheduleWindow(frozenset(range(7)), time(9), time(22)),)
    floor = RoomConfig(
        name="bath", floor_heating=True, schedule=window, lead_time=__import__("datetime").timedelta(hours=3)
    )
    other = RoomConfig(name="hall")  # no schedule: setback
    inp = EngineInput(
        config=EngineConfig(rooms=(floor, other), easycontrol_low=10.0, easycontrol_high=22.0),
        now=clock.now(), anyone_home=True, learned={}, last_commands=Commands(),
        external_temps={"bath": SensorReading(17.0, clock.now())},
        trv_temps={"hall": SensorReading(15.5, clock.now())},
    )
    d = decide(inp)
    assert d.reasons["bath"] == "pre_heat" and d.demand_rooms == ("bath",)
    assert (d.trv_setpoints["hall"], d.reasons["hall"]) == (12.0, "floor_first")
    assert d.external_temp_pushes == {}  # floor room has no TRV to push to
    warm = decide(__import__("dataclasses").replace(inp, external_temps={"bath": SensorReading(19.4, clock.now())}))
    assert warm.reasons["hall"] == "setback"


def _open_radiator_home(clock, living_temp):
    from datetime import time

    from custom_components.smart_heating.engine import (
        Commands, EngineConfig, EngineInput, RoomConfig, ScheduleWindow, SensorReading, decide,
    )

    clock.advance(hours=9)  # 12:00, inside both windows
    window = (ScheduleWindow(frozenset(range(7)), time(6), time(23)),)
    living = RoomConfig(name="living", open_radiators=True, schedule=window)
    bedroom = RoomConfig(name="bedroom", schedule=window)
    return decide(
        EngineInput(
            config=EngineConfig(rooms=(living, bedroom), easycontrol_low=10.0, easycontrol_high=22.0),
            now=clock.now(), anyone_home=True, learned={}, last_commands=Commands(),
            external_temps={"living": SensorReading(living_temp, clock.now())},
            trv_temps={"bedroom": SensorReading(17.0, clock.now())},
        )
    )


def test_open_radiator_room_at_comfort_stops_the_boiler_call_of_other_rooms(clock):
    d = _open_radiator_home(clock, living_temp=19.6)
    assert d.demand_rooms == () and d.easycontrol_setpoint == 10.0
    assert d.external_temp_pushes == {}  # no TRV to push to


def test_open_radiator_room_below_comfort_lets_the_boiler_call_through(clock):
    d = _open_radiator_home(clock, living_temp=18.0)
    assert set(d.demand_rooms) == {"living", "bedroom"} and d.easycontrol_setpoint == 22.0
