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
        ).trv_setpoints

    away = run(anyone_home=False, away_since=now - timedelta(hours=1))
    assert away["boosted"] == 20.0  # Boost beats window pause and Away
    assert away["falling"] == 12.0  # window pause beats Away (setback)
    assert away["steady"] == 16.0  # Away beats schedule (comfort)

    vacation = run(anyone_home=True, vacation_until=now + timedelta(days=3))
    assert vacation["boosted"] == 20.0
    assert vacation["steady"] == 12.0  # Vacation beats schedule
    away_only = run(anyone_home=True)
    assert away_only["steady"] == 20.0  # schedule when nobody overrides
