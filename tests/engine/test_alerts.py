from datetime import timedelta

from custom_components.smart_heating.engine import (
    AlertConfig,
    AlertNotifier,
    Commands,
    EngineConfig,
    EngineInput,
    RoomConfig,
    SensorReading,
    WriteResult,
    decide,
    track_unmet,
)


def make_input(clock, **overrides) -> EngineInput:
    defaults = dict(
        config=EngineConfig(
            rooms=(RoomConfig(name="bedroom"),), easycontrol_low=10.0, easycontrol_high=22.0
        ),
        now=clock.now(),
        anyone_home=True,
        room_temps={},
        learned={},
        last_commands=Commands(),
        trv_temps={"bedroom": SensorReading(17.0, clock.now())},
        trv_last_seen={"bedroom": clock.now()},
    )
    defaults.update(overrides)
    return EngineInput(**defaults)


def codes(decision):
    return {(a.code, a.room) for a in decision.alerts}


def failed(clock, n):
    return WriteResult(at=clock.now(), status="error", consecutive_failures=n)


def test_healthy_system_raises_no_alerts(clock):
    assert decide(make_input(clock)).alerts == ()


def test_trv_offline_after_60_minutes_and_clears_when_it_reports(clock):
    seen = clock.now() - timedelta(minutes=59)
    assert codes(decide(make_input(clock, trv_last_seen={"bedroom": seen}))) == set()
    seen = clock.now() - timedelta(minutes=61)
    assert ("trv_offline", "bedroom") in codes(
        decide(make_input(clock, trv_last_seen={"bedroom": seen}))
    )
    assert codes(decide(make_input(clock))) == set()


def test_room_without_trv_report_history_raises_no_offline_alert(clock):
    assert decide(make_input(clock, trv_last_seen={})).alerts == ()


def test_low_battery_fires_and_clears(clock):
    assert ("low_battery", "bedroom") in codes(
        decide(make_input(clock, battery_low={"bedroom": True}))
    )
    assert decide(make_input(clock, battery_low={"bedroom": False})).alerts == ()


def test_room_never_reaches_target_uses_configurable_window(clock):
    since = clock.now() - timedelta(hours=2, minutes=59)
    assert decide(make_input(clock, unmet_since={"bedroom": since})).alerts == ()
    since = clock.now() - timedelta(hours=3, minutes=1)
    assert ("target_not_reached", "bedroom") in codes(
        decide(make_input(clock, unmet_since={"bedroom": since}))
    )
    cfg = EngineConfig(
        rooms=(RoomConfig(name="bedroom"),),
        easycontrol_low=10.0,
        easycontrol_high=22.0,
        alerts=AlertConfig(target_window=timedelta(hours=1)),
    )
    since = clock.now() - timedelta(hours=1, minutes=1)
    assert ("target_not_reached", "bedroom") in codes(
        decide(make_input(clock, config=cfg, unmet_since={"bedroom": since}))
    )


def test_track_unmet_starts_keeps_and_resets(clock):
    t0 = clock.now()
    since = track_unmet({}, t0, {"bedroom": 17.0}, {"bedroom": 19.5})
    assert since == {"bedroom": t0}
    later = t0 + timedelta(hours=1)
    assert track_unmet(since, later, {"bedroom": 18.0}, {"bedroom": 19.5}) == since
    assert track_unmet(since, later, {"bedroom": 19.5}, {"bedroom": 19.5}) == {}


def test_bosch_outage_alert_after_three_failed_writes(clock):
    assert decide(make_input(clock, last_write=failed(clock, 2))).alerts == ()
    d = decide(make_input(clock, last_write=failed(clock, 3)))
    assert ("bosch_outage", None) in codes(d)
    ok = WriteResult(at=clock.now(), status="ok")
    assert decide(make_input(clock, last_write=ok)).alerts == ()


def test_outage_keeps_last_setpoints_and_does_not_flood_writes(clock):
    # 03:00 is outside any schedule and the room is cold: normally this would change setpoints.
    commands = Commands(
        trv_setpoints={"bedroom": 19.5},
        easycontrol_setpoint=10.0,
        easycontrol_changed_at=clock.now() - timedelta(hours=1),
    )
    d = decide(make_input(clock, last_commands=commands, last_write=failed(clock, 3)))
    assert d.trv_setpoints == {"bedroom": 19.5}
    assert d.easycontrol_setpoint == 10.0


def test_notifier_notifies_once_and_dismisses_on_resolution(clock):
    n = AlertNotifier()
    a = decide(make_input(clock, battery_low={"bedroom": True})).alerts
    first = n.update(a)
    assert [x.code for x in first.raised] == ["low_battery"] and first.cleared == ()
    again = n.update(a)
    assert again.raised == () and again.cleared == ()
    done = n.update(())
    assert done.raised == () and [x.code for x in done.cleared] == ["low_battery"]
