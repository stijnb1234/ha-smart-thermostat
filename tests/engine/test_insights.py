from datetime import UTC, datetime, time, timedelta

from custom_components.smart_heating.engine import (
    Commands,
    EngineConfig,
    EngineInput,
    RoomConfig,
    SensorConfig,
    SensorReading,
    decide,
)
from custom_components.smart_heating.engine.boiler import demand_rooms
from custom_components.smart_heating.engine.insights import RoomInsights
from custom_components.smart_heating.engine.sensors import select_temperature
from custom_components.smart_heating.engine.trackers import CoastTracker, StallTracker

T0 = datetime(2026, 1, 12, 12, 0, tzinfo=UTC)


def minutes(n):
    return T0 + timedelta(minutes=n)


# --- learned open-window threshold -------------------------------------------------

def test_window_threshold_needs_data_and_never_exceeds_the_configured_drop():
    ins = RoomInsights()
    assert ins.window_threshold("bed", 1.5) is None
    for _ in range(40):
        ins.record_drop("bed", 0.1)
    assert ins.window_threshold("bed", 1.5) == 0.5  # quiet room: 0.1 + 0.4 margin, floor 0.5
    assert ins.window_threshold("bed", 0.5) == 0.5


def test_noisy_room_learns_a_higher_threshold():
    ins = RoomInsights()
    for i in range(100):
        ins.record_drop("bed", 0.6 if i % 4 == 0 else 0.1)
    assert 0.9 <= ins.window_threshold("bed", 1.5) <= 1.1


def test_learned_threshold_beats_a_stale_stored_drop(clock):
    room = RoomConfig(name="bed", window_drop=1.5)
    inp = EngineInput(
        config=EngineConfig(rooms=(room,), boiler_low=10.0, boiler_high=22.0),
        now=minutes(0), anyone_home=True, learned={}, last_commands=Commands(),
        trv_temps={"bed": SensorReading(18.0, minutes(0))},
        temp_history={"bed": (SensorReading(19.0, minutes(-8)), SensorReading(18.0, minutes(0)))},
    )
    assert "bed" not in decide(inp).window_paused_until
    import dataclasses

    learned = dataclasses.replace(inp, window_thresholds={"bed": 0.7})
    assert "bed" in decide(learned).window_paused_until


# --- coast: end the call early -------------------------------------------------------

def test_coast_tracker_measures_the_rise_after_the_call_ends():
    t = CoastTracker()
    assert t.observe("bed", minutes(0), 19.0, calling=True) is None
    assert t.observe("bed", minutes(1), 19.3, calling=False) is None  # call just ended here
    assert t.observe("bed", minutes(5), 19.8, calling=False) is None
    assert t.observe("bed", minutes(9), 19.9, calling=False) is None
    assert t.observe("bed", minutes(12), 19.7, calling=False) == pytest_approx(0.6)


def test_coast_tracker_ignores_calls_ended_by_something_else():
    t = CoastTracker()
    t.observe("bed", minutes(0), 19.0, calling=True)
    t.observe("bed", minutes(1), 19.3, calling=False, valid=False)  # window pause
    assert t.observe("bed", minutes(20), 18.0, calling=False) is None


def test_learned_coast_widens_the_demand_margin():
    room = RoomConfig(name="bed", comfort=19.5)
    cfg = EngineConfig(rooms=(room,), boiler_low=10.0, boiler_high=22.0)
    temps, targets = {"bed": 19.0}, {"bed": 19.5}
    assert demand_rooms(cfg, targets, temps) == ("bed",)  # 0.5 below target, hysteresis 0.3
    assert demand_rooms(cfg, targets, temps, coast={"bed": 0.6}) == ()  # it will coast the rest


def test_coast_needs_three_observations_and_is_capped():
    ins = RoomInsights()
    ins.record_coast("bed", 5.0)
    ins.record_coast("bed", 5.0)
    assert ins.coast("bed") is None
    ins.record_coast("bed", 5.0)
    assert ins.coast("bed") == 1.0


# --- sensor offset ----------------------------------------------------------------------

def test_learned_offset_fixes_the_trv_fallback_unless_one_is_configured():
    cfg = SensorConfig()
    trv = {"bed": SensorReading(18.0, minutes(0))}
    plain = RoomConfig(name="bed")
    assert select_temperature(plain, {}, trv, minutes(1), cfg)[0] == 18.0
    assert select_temperature(plain, {}, trv, minutes(1), cfg, {"bed": 1.2})[0] == 19.2
    manual = RoomConfig(name="bed", trv_offset=-0.5)
    assert select_temperature(manual, {}, trv, minutes(1), cfg, {"bed": 1.2})[0] == 17.5


def test_offset_is_the_median_of_enough_samples():
    ins = RoomInsights()
    for _ in range(23):
        ins.record_offset("bed", 1.0)
    assert ins.offset("bed") is None
    ins.record_offset("bed", 9.0)
    assert ins.offset("bed") == 1.0


# --- stall ------------------------------------------------------------------------------

def test_stall_after_45_minutes_of_calling_without_warming_up():
    s = StallTracker()
    for m in range(0, 46, 5):
        s.observe("bed", minutes(m), 18.0 + (0.1 if m else 0), calling=True)
    assert s.stalled(minutes(45)) == frozenset({"bed"})


def test_progress_or_stopping_resets_the_stall():
    s = StallTracker()
    for m in range(0, 40, 5):
        s.observe("bed", minutes(m), 18.0, calling=True)
    s.observe("bed", minutes(40), 18.4, calling=True)  # real warming
    assert s.stalled(minutes(50)) == frozenset()
    s.observe("bed", minutes(60), 18.4, calling=False)
    assert s.stalled(minutes(120)) == frozenset()


def test_stalled_room_raises_an_alert():
    room = RoomConfig(name="bed")
    inp = EngineInput(
        config=EngineConfig(rooms=(room,), boiler_low=10.0, boiler_high=22.0),
        now=minutes(0), anyone_home=True, learned={}, last_commands=Commands(),
        trv_temps={"bed": SensorReading(18.0, minutes(0))}, stalled=frozenset({"bed"}),
    )
    assert [(a.code, a.room) for a in decide(inp).alerts] == [("not_warming", "bed")]


# --- schedule suggestions ---------------------------------------------------------------

def _never_covered(room, at):
    return False


def test_three_days_of_morning_boosts_become_a_suggestion():
    ins = RoomInsights()
    for day in (0, 1, 3):  # Mon, Tue, Thu
        ins.record_event("study", datetime(2026, 1, 12 + day, 7, 10 + day, tzinfo=UTC))
    (s,) = ins.suggestions(datetime(2026, 1, 16, tzinfo=UTC), _never_covered)
    assert (s.room, s.days, s.start, s.events) == ("study", (0, 1, 3), time(7, 10), 3)


def test_two_days_or_covered_moments_are_not_suggested():
    ins = RoomInsights()
    for day in (0, 1):
        ins.record_event("study", datetime(2026, 1, 12 + day, 7, 0, tzinfo=UTC))
    assert ins.suggestions(datetime(2026, 1, 16, tzinfo=UTC), _never_covered) == []
    ins.record_event("study", datetime(2026, 1, 14, 7, 0, tzinfo=UTC))
    assert ins.suggestions(datetime(2026, 1, 16, tzinfo=UTC), lambda r, at: True) == []


def test_old_events_expire():
    ins = RoomInsights()
    for day in (0, 1, 2):
        ins.record_event("study", datetime(2026, 1, 12 + day, 7, 0, tzinfo=UTC))
    assert ins.suggestions(datetime(2026, 3, 1, tzinfo=UTC), _never_covered) == []


def test_insights_survive_a_roundtrip_and_bad_data_is_ignored():
    ins = RoomInsights()
    for _ in range(40):
        ins.record_drop("bed", 0.2)
    ins.record_event("bed", T0)
    again = RoomInsights.from_dict(ins.to_dict())
    assert again.window_threshold("bed", 1.5) == ins.window_threshold("bed", 1.5)
    assert again.to_dict() == ins.to_dict()
    assert RoomInsights.from_dict({"version": 99}).to_dict() == RoomInsights().to_dict()
    assert RoomInsights.from_dict({"version": 1, "drops": {"bed": ["x"]}}).to_dict() == RoomInsights().to_dict()


def pytest_approx(value):
    import pytest

    return pytest.approx(value)
