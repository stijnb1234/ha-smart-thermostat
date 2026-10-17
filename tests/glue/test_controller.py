from datetime import datetime, time, timedelta, timezone

from custom_components.smart_heating.controller import Controller, Snapshot
from custom_components.smart_heating.engine import (
    Boost,
    Commands,
    EngineConfig,
    RoomConfig,
    ScheduleWindow,
    SensorReading,
)
from custom_components.smart_heating.engine.learner import LeadTimeLearner
from custom_components.smart_heating.gather import (
    battery_entity,
    battery_is_low,
    parse_number,
    update_history,
    z2m_name,
)

UTC = timezone.utc
T0 = datetime(2026, 1, 12, 3, 0, tzinfo=UTC)  # Monday 03:00
ROOM = RoomConfig(
    name="work",
    comfort=20.0,
    setback=16.0,
    schedule=(ScheduleWindow(frozenset({0}), time(8), time(17)),),
)
CONFIG = EngineConfig(rooms=(ROOM,), easycontrol_low=10.0, easycontrol_high=22.0)


def snap(now, temp=17.0, ext=None, **kw):
    return Snapshot(
        now=now,
        external={"work": SensorReading(ext, now)} if ext is not None else {},
        trv={"work": SensorReading(temp, now)},
        trv_last_seen={"work": now},
        battery_low={},
        anyone_home=True,
        away_since=None,
        vacation_until=None,
        outdoor_temp=kw.pop("outdoor_temp", 2.0),
        last_write=None,
        **kw,
    )


def make(boosts=None, learner=None):
    return Controller(CONFIG, learner or LeadTimeLearner(), boosts or {}, {})


def test_step_decides_and_explains():
    c = make()
    cycle = c.step(snap(T0))
    assert cycle.decision.trv_setpoints["work"] == 16.0
    assert cycle.explanations["work"].reason == "setback"
    assert cycle.lead_times["work"] == timedelta(minutes=70)


def test_boost_from_shared_dict_is_used():
    boosts = {"work": Boost(T0, timedelta(minutes=60))}
    cycle = make(boosts).step(snap(T0))
    assert cycle.explanations["work"].reason == "boost"


def test_external_push_not_repeated_after_confirm():
    c = make()
    first = c.step(snap(T0, ext=17.0))
    assert first.decision.external_temp_pushes == {"work": 17.0}
    c.confirm(first, {"work": 16.0}, Commands())
    second = c.step(snap(T0 + timedelta(minutes=1), ext=17.0))
    assert second.decision.external_temp_pushes == {}


def test_window_pause_is_fed_back_and_persists():
    c = make()
    c.step(snap(T0, temp=19.0))
    cycle = c.step(snap(T0 + timedelta(minutes=2), temp=17.0))  # 2 K drop
    assert cycle.explanations["work"].reason == "window"
    c.confirm(cycle, {"work": 12.0}, Commands())
    # temperature stabilises, pause still holds from last_commands
    later = c.step(snap(T0 + timedelta(minutes=5), temp=17.0))
    assert later.explanations["work"].reason == "window"


def test_unmet_target_alert_after_window():
    c = make()
    alerts = ()
    for minutes in range(0, 4 * 60 + 1, 30):
        # in setback window at 3am-7am? keep room below its setback of 16
        cycle = c.step(snap(T0 + timedelta(minutes=minutes), temp=14.0))
        alerts = cycle.decision.alerts
    assert any(a.code == "target_not_reached" for a in alerts)


def test_trv_offline_alert():
    c = make()
    s = snap(T0)
    old = Snapshot(**{**s.__dict__, "trv_last_seen": {"work": T0 - timedelta(hours=2)}})
    assert any(a.code == "trv_offline" for a in c.step(old).decision.alerts)


def test_learned_lead_time_used_and_warmup_recorded():
    learner = LeadTimeLearner()
    c = make(learner=learner)
    start = datetime(2026, 1, 12, 7, 0, tzinfo=UTC)  # inside pre-heat (default 70 min)
    c.step(snap(start, temp=16.0))
    c.step(snap(start + timedelta(minutes=30), temp=18.0))
    assert not c.learner_dirty
    c.step(snap(start + timedelta(minutes=60), temp=19.9))
    assert c.learner_dirty
    # 4 K in 1 h -> 4 K/h sample stored
    assert learner.to_dict()["rooms"]["work"] == [{"outdoor": 2.0, "rate": 4.0}]


def test_warmup_cancelled_when_target_drops():
    learner = LeadTimeLearner()
    c = make(learner=learner)
    start = datetime(2026, 1, 12, 7, 0, tzinfo=UTC)
    c.step(snap(start, temp=16.0))
    c.step(snap(start - timedelta(hours=5), temp=16.0))  # goes back to setback
    c.step(snap(start + timedelta(minutes=60), temp=19.9))
    assert not c.learner_dirty


def test_gather_helpers():
    assert parse_number("19.5") == 19.5
    assert parse_number("unavailable") is None
    assert parse_number(None) is None
    h = update_history((), SensorReading(1.0, T0), T0, timedelta(minutes=30))
    h = update_history(h, SensorReading(2.0, T0 + timedelta(minutes=40)), T0 + timedelta(minutes=40), timedelta(minutes=30))
    assert [r.value for r in h] == [2.0]
    assert z2m_name("climate.bedroom_trv") == "bedroom_trv"
    assert battery_entity("climate.bedroom_trv") == "sensor.bedroom_trv_battery"
    assert battery_is_low("15") and not battery_is_low("80") and not battery_is_low("unknown")
