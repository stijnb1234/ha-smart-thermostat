from dataclasses import replace
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

ALWAYS = (ScheduleWindow(frozenset(range(7)), time(0), time(23, 59)),)
TARGET = 19.5  # comfort
OLD = 16.0


def make(clock, observed, written_ago=15, previous=OLD, retries=0, manual=None, target_written=TARGET):
    cfg = EngineConfig(
        rooms=(RoomConfig(name="office", comfort=TARGET, schedule=ALWAYS),),
        easycontrol_low=10.0,
        easycontrol_high=22.0,
    )
    cmds = Commands(
        trv_setpoints={"office": target_written},
        trv_written_at={"office": clock.now() - timedelta(minutes=written_ago)},
        trv_previous={} if previous is None else {"office": previous},
        trv_retries={"office": retries} if retries else {},
        trv_manual=manual or {},
    )
    return EngineInput(
        config=cfg,
        now=clock.now(),
        anyone_home=True,
        learned={},
        last_commands=cmds,
        trv_temps={"office": SensorReading(19.0, clock.now())},
        trv_observed={} if observed is None else {"office": observed},
    )


def codes(d):
    return {a.code for a in d.alerts}


def test_matching_observed_needs_nothing(clock):
    d = decide(make(clock, TARGET))

    assert not d.trv_rewrite and not d.trv_manual and "trv_write_failed" not in codes(d)


def test_unavailable_observed_does_nothing(clock):
    d = decide(make(clock, None))

    assert not d.trv_rewrite and not d.trv_manual


def test_mismatch_before_settle_is_ignored(clock):
    d = decide(make(clock, OLD, written_ago=9))

    assert not d.trv_rewrite and not d.trv_manual


def test_lost_write_is_rewritten_after_settle(clock):
    d = decide(make(clock, OLD))

    assert d.trv_rewrite == frozenset({"office"})
    assert d.trv_retries == {"office": 1}


def test_other_value_is_manual_change_and_left_alone(clock):
    d = decide(make(clock, 21.0))

    assert not d.trv_rewrite
    assert d.trv_manual == {"office": TARGET}


def test_manual_room_stays_alone_while_target_is_unchanged(clock):
    d = decide(make(clock, 21.0, manual={"office": TARGET}))

    assert not d.trv_rewrite and d.trv_manual == {"office": TARGET}


def test_manual_cleared_when_target_changes(clock):
    # Written 16 earlier, user set 21; target is now 19.5 again.
    d = decide(make(clock, 21.0, manual={"office": OLD}, target_written=OLD))

    assert not d.trv_manual


def test_retries_stop_after_three_and_raise_alert(clock):
    d = decide(make(clock, OLD, retries=3))

    assert not d.trv_rewrite
    assert "trv_write_failed" in codes(d)
    assert d.trv_retries == {"office": 3}


def test_third_retry_still_allowed(clock):
    d = decide(make(clock, OLD, retries=2))

    assert d.trv_rewrite == frozenset({"office"}) and d.trv_retries == {"office": 3}


def test_retry_alert_cleared_when_value_matches(clock):
    d = decide(make(clock, TARGET, retries=3))

    assert "trv_write_failed" not in codes(d) and not d.trv_retries


def test_unknown_previous_value_with_mismatch_is_manual(clock):
    d = decide(make(clock, OLD, previous=None))

    assert not d.trv_rewrite and d.trv_manual == {"office": TARGET}


def test_settle_is_configurable(clock):
    inp = make(clock, OLD, written_ago=5)
    inp = replace(inp, config=replace(inp.config, trv_settle=timedelta(minutes=5)))

    assert decide(inp).trv_rewrite == frozenset({"office"})
