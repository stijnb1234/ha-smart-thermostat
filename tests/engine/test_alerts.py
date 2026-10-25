from datetime import timedelta

from custom_components.smart_heating.engine import (
    Alert,
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
    defaults = {
        "config": EngineConfig(
            rooms=(RoomConfig(name="bedroom"),), boiler_low=10.0, boiler_high=22.0
        ),
        "now": clock.now(),
        "anyone_home": True,
        "learned": {},
        "last_commands": Commands(),
        "trv_temps": {"bedroom": SensorReading(17.0, clock.now())},
        "trv_last_seen": {"bedroom": clock.now()},
    }
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
        boiler_low=10.0,
        boiler_high=22.0,
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


def test_boiler_outage_alert_after_three_failed_writes(clock):
    assert decide(make_input(clock, last_write=failed(clock, 2))).alerts == ()
    d = decide(make_input(clock, last_write=failed(clock, 3)))
    assert ("boiler_outage", None) in codes(d)
    ok = WriteResult(at=clock.now(), status="ok")
    assert decide(make_input(clock, last_write=ok)).alerts == ()


def test_outage_does_not_freeze_trv_setpoints_but_throttles_boiler_writes(clock):
    # Boost must still reach the TRVs during a Bosch outage: TRVs do not use the cloud.
    from custom_components.smart_heating.engine import Boost

    commands = Commands(
        trv_setpoints={"bedroom": 16.0},
        boiler_setpoint=10.0,
        boiler_changed_at=clock.now() - timedelta(hours=1),
    )
    boost = {"bedroom": Boost(clock.now(), timedelta(minutes=60))}
    d = decide(
        make_input(clock, last_commands=commands, last_write=failed(clock, 3), boosts=boost)
    )
    assert d.trv_setpoints == {"bedroom": 19.5}
    assert d.boiler_setpoint == 10.0  # backoff still holds the boiler call


def test_stale_external_sensor_alerts_after_two_hours(clock):
    def alerts(age):
        ext = {"bedroom": SensorReading(18.0, clock.now() - age)}
        return codes(decide(make_input(clock, external_temps=ext)))

    assert ("sensor_stale", "bedroom") not in alerts(timedelta(hours=1, minutes=59))
    assert ("sensor_stale", "bedroom") in alerts(timedelta(hours=2, minutes=1))


def test_notifier_notifies_once_and_dismisses_on_resolution(clock):
    n = AlertNotifier()
    a = decide(make_input(clock, battery_low={"bedroom": True})).alerts
    first = n.update(a)
    assert [x.code for x in first.raised] == ["low_battery"] and first.cleared == ()
    again = n.update(a)
    assert again.raised == () and again.cleared == ()
    done = n.update(())
    assert done.raised == () and [x.code for x in done.cleared] == ["low_battery"]


def test_track_unmet_ignores_rooms_within_their_margin(clock):
    t0 = clock.now()
    # 19.3 against 19.5 with a 0.3 K margin: inside the band the boiler deliberately leaves alone.
    assert track_unmet({}, t0, {"bedroom": 19.3}, {"bedroom": 19.5}, {"bedroom": 0.3}) == {}
    assert track_unmet({}, t0, {"bedroom": 19.1}, {"bedroom": 19.5}, {"bedroom": 0.3}) == {"bedroom": t0}


def test_push_waits_until_an_alert_has_lasted_the_delay_and_reports_resolution_once(clock):
    from custom_components.smart_heating.engine.alerts import AlertPush

    push = AlertPush(delay=timedelta(minutes=15))
    offline = Alert("trv_offline", "bedroom")
    t0 = clock.now()
    assert push.update((offline,), t0).raised == ()
    assert push.update((offline,), t0 + timedelta(minutes=14)).raised == ()
    assert push.update((offline,), t0 + timedelta(minutes=15)).raised == (offline,)
    assert push.update((offline,), t0 + timedelta(minutes=16)).raised == ()  # once
    assert push.update((), t0 + timedelta(minutes=20)).cleared == (offline,)


def test_push_ignores_an_alert_that_clears_within_the_delay(clock):
    from custom_components.smart_heating.engine.alerts import AlertPush

    push = AlertPush(delay=timedelta(minutes=15))
    t0 = clock.now()
    push.update((Alert("trv_offline", "bedroom"),), t0)
    changes = push.update((), t0 + timedelta(minutes=5))
    assert changes.raised == () and changes.cleared == ()
    # A flap restarts the wait.
    push.update((Alert("trv_offline", "bedroom"),), t0 + timedelta(minutes=6))
    assert push.update((Alert("trv_offline", "bedroom"),), t0 + timedelta(minutes=20)).raised == ()
