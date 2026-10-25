from datetime import time, timedelta

from custom_components.smart_heating.engine import (
    Commands,
    EngineConfig,
    EngineInput,
    RoomConfig,
    ScheduleWindow,
    SensorReading,
    WriteResult,
    decide,
)

LOW, HIGH = 10.0, 22.0
# Always at comfort (19.5) so cold readings are real demand.
ALWAYS = (ScheduleWindow(frozenset(range(7)), time(0), time(23, 59)),)


def make_input(clock, temps=None, commands=None, last_write=None) -> EngineInput:
    config = EngineConfig(
        rooms=(
            RoomConfig(name="bedroom", comfort=19.5, setback=16.0, schedule=ALWAYS),
            RoomConfig(name="office", comfort=19.5, setback=16.0, schedule=ALWAYS),
        ),
        boiler_low=LOW,
        boiler_high=HIGH,
    )
    return EngineInput(
        config=config,
        now=clock.now(),
        anyone_home=True,
        trv_temps={
            name: SensorReading(value=value, at=clock.now())
            for name, value in (temps or {"bedroom": 17.0, "office": 17.0}).items()
        },
        learned={},
        last_commands=commands or Commands(),
        last_write=last_write,
    )


def held(clock, setpoint, ago_minutes):
    return Commands(
        boiler_setpoint=setpoint,
        boiler_changed_at=clock.now() - timedelta(minutes=ago_minutes),
    )


def test_no_demand_calls_low(clock):
    # Both rooms within the hysteresis of their comfort target.
    d = decide(make_input(clock, temps={"bedroom": 19.5, "office": 19.3}))

    assert d.boiler_setpoint == LOW


def test_demand_in_one_room_raises_setpoint(clock):
    d = decide(make_input(clock, temps={"bedroom": 17.0, "office": 15.0}))

    assert d.boiler_setpoint == HIGH


def test_room_without_reading_creates_no_demand(clock):
    d = decide(make_input(clock, temps={"bedroom": 19.4}))

    assert d.boiler_setpoint == LOW


def test_change_within_debounce_window_is_held_back(clock):
    cmds = held(clock, LOW, ago_minutes=2)

    d = decide(make_input(clock, temps={"office": 15.0}, commands=cmds))

    assert d.boiler_setpoint == LOW


def test_change_allowed_after_debounce_window(clock):
    cmds = held(clock, LOW, ago_minutes=5)

    d = decide(make_input(clock, temps={"office": 15.0}, commands=cmds))

    assert d.boiler_setpoint == HIGH


def test_lowering_is_debounced_too(clock):
    cmds = held(clock, HIGH, ago_minutes=1)

    d = decide(make_input(clock, temps={"office": 19.6, "bedroom": 19.6}, commands=cmds))

    assert d.boiler_setpoint == HIGH


def test_rate_limited_write_backs_off_five_minutes_then_retries(clock):
    cmds = held(clock, LOW, ago_minutes=60)
    result = WriteResult(at=clock.now(), status="rate_limited", consecutive_failures=1)
    temps = {"office": 15.0}

    assert decide(make_input(clock, temps, cmds, result)).boiler_setpoint == LOW
    clock.advance(minutes=4)
    assert decide(make_input(clock, temps, cmds, result)).boiler_setpoint == LOW
    clock.advance(minutes=1)
    assert decide(make_input(clock, temps, cmds, result)).boiler_setpoint == HIGH


def test_backoff_doubles_and_caps_at_thirty_minutes(clock):
    cmds = held(clock, LOW, ago_minutes=600)
    temps = {"office": 15.0}

    def setpoint_after(failures, minutes):
        result = WriteResult(
            at=clock.now() - timedelta(minutes=minutes),
            status="rate_limited",
            consecutive_failures=failures,
        )
        return decide(make_input(clock, temps, cmds, result)).boiler_setpoint

    assert setpoint_after(2, 9) == LOW
    assert setpoint_after(2, 10) == HIGH
    assert setpoint_after(3, 19) == LOW
    assert setpoint_after(3, 20) == HIGH
    assert setpoint_after(9, 29) == LOW
    assert setpoint_after(9, 30) == HIGH


def test_retry_after_overrides_computed_backoff(clock):
    cmds = held(clock, LOW, ago_minutes=600)
    result = WriteResult(
        at=clock.now() - timedelta(minutes=6),
        status="rate_limited",
        retry_after=timedelta(minutes=15),
        consecutive_failures=1,
    )

    d = decide(make_input(clock, {"office": 15.0}, cmds, result))

    assert d.boiler_setpoint == LOW


def test_other_write_errors_use_same_backoff(clock):
    cmds = held(clock, LOW, ago_minutes=600)
    result = WriteResult(at=clock.now(), status="error", consecutive_failures=1)

    d = decide(make_input(clock, {"office": 15.0}, cmds, result))

    assert d.boiler_setpoint == LOW


def test_successful_write_result_does_not_delay(clock):
    cmds = held(clock, LOW, ago_minutes=600)
    result = WriteResult(at=clock.now() - timedelta(minutes=10), status="ok")

    d = decide(make_input(clock, {"office": 15.0}, cmds, result))

    assert d.boiler_setpoint == HIGH


def test_first_write_during_backoff_is_not_attempted(clock):
    # Nothing written yet (adapter holds None) and the first attempt got a 429.
    result = WriteResult(at=clock.now() - timedelta(minutes=1), status="rate_limited", consecutive_failures=1)

    d = decide(make_input(clock, {"office": 15.0}, Commands(), result))

    assert d.boiler_setpoint is None


def test_first_write_allowed_once_backoff_has_passed(clock):
    result = WriteResult(at=clock.now() - timedelta(minutes=5), status="rate_limited", consecutive_failures=1)

    d = decide(make_input(clock, {"office": 15.0}, Commands(), result))

    assert d.boiler_setpoint == HIGH


def test_at_most_one_write_per_minimum_interval_even_without_debounce(clock):
    from dataclasses import replace

    inp = make_input(clock, {"office": 15.0}, held(clock, LOW, ago_minutes=1))
    inp = replace(inp, config=replace(inp.config, boiler_debounce=timedelta(0)))

    assert decide(inp).boiler_setpoint == LOW
    clock.advance(minutes=1)
    inp = replace(inp, now=clock.now())
    assert decide(inp).boiler_setpoint == HIGH


def test_setback_room_slightly_cold_creates_no_demand(clock):
    from dataclasses import replace

    inp = make_input(clock, {"office": 15.9, "bedroom": 15.9})
    rooms = tuple(replace(r, schedule=()) for r in inp.config.rooms)  # setback all day
    inp = replace(inp, config=replace(inp.config, rooms=rooms))

    assert decide(inp).boiler_setpoint == LOW


def test_comfort_room_demand_needs_to_exceed_hysteresis(clock):
    assert decide(make_input(clock, {"office": 19.25})).boiler_setpoint == LOW
    assert decide(make_input(clock, {"office": 19.15})).boiler_setpoint == HIGH


def test_hysteresis_is_configurable(clock):
    from dataclasses import replace

    inp = make_input(clock, {"office": 19.25})
    inp = replace(inp, config=replace(inp.config, demand_hysteresis=0.1))

    assert decide(inp).boiler_setpoint == HIGH


def _observed(clock, observed, held_ago, last_write=None, hold_ago=None, hold_for=None, setpoint=HIGH, temps=None):
    from dataclasses import replace

    cmds = held(clock, setpoint, held_ago)
    if hold_for is not None:
        cmds = replace(cmds, boiler_hold_until=clock.now() + timedelta(minutes=hold_for))
    inp = make_input(clock, temps or {"office": 15.0}, cmds, last_write)
    return replace(inp, boiler_observed=observed)


# Manual change on the boiler thermostat: respected for a while, then we resume.
# (Replaces the old "re-assert after 30 min of drift", which reverted a hand change within a minute or so.)


def test_difference_right_after_our_write_is_not_yet_manual(clock):
    d = decide(_observed(clock, observed=18.0, held_ago=9))

    assert d.boiler_hold_until is None and not d.boiler_reassert
    assert d.boiler_setpoint == HIGH


def test_difference_after_settle_starts_a_two_hour_hold_without_writing(clock):
    d = decide(_observed(clock, observed=18.0, held_ago=10))

    assert d.boiler_hold_until == clock.now() + timedelta(hours=2)
    assert d.boiler_setpoint == HIGH and not d.boiler_reassert


def test_no_writes_during_hold_even_if_demand_changes(clock):
    d = decide(_observed(clock, 18.0, 60, hold_for=60, temps={"office": 19.6, "bedroom": 19.6}))

    assert d.boiler_setpoint == HIGH  # held value: adapter stays quiet
    assert not d.boiler_reassert
    assert d.boiler_hold_until == clock.now() + timedelta(minutes=60)


def test_after_hold_a_differing_observed_setpoint_is_rewritten(clock):
    d = decide(_observed(clock, 18.0, 130, hold_for=-1))

    assert d.boiler_setpoint == HIGH and d.boiler_reassert
    assert d.boiler_hold_until is None


def test_after_hold_a_changed_desire_is_written_normally(clock):
    d = decide(_observed(clock, 18.0, 130, hold_for=-1, temps={"office": 19.6, "bedroom": 19.6}))

    assert d.boiler_setpoint == LOW and d.boiler_hold_until is None


def test_after_hold_blocked_write_keeps_state_instead_of_new_hold(clock):
    result = WriteResult(at=clock.now(), status="rate_limited", consecutive_failures=1)

    d = decide(_observed(clock, 18.0, 130, result, hold_for=-1))

    assert not d.boiler_reassert
    assert d.boiler_hold_until is not None and d.boiler_hold_until <= clock.now()


def test_after_hold_matching_observed_clears_hold(clock):
    d = decide(_observed(clock, HIGH, 130, hold_for=-1))

    assert d.boiler_hold_until is None and not d.boiler_reassert


def test_hold_length_and_settle_are_configurable(clock):
    from dataclasses import replace

    inp = _observed(clock, 18.0, 5)
    cfg = replace(
        inp.config, boiler_settle=timedelta(minutes=4), boiler_manual_hold=timedelta(hours=1)
    )
    d = decide(replace(inp, config=cfg))

    assert d.boiler_hold_until == clock.now() + timedelta(hours=1)


def test_matching_observed_setpoint_starts_no_hold(clock):
    assert decide(_observed(clock, HIGH, 90)).boiler_hold_until is None


def test_unknown_observed_setpoint_starts_no_hold(clock):
    assert decide(_observed(clock, None, 90)).boiler_hold_until is None


def test_hand_value_matching_our_desire_is_adopted_instead_of_a_new_hold(clock):
    # We held LOW; someone turned the thermostat up to HIGH by hand. The hold ends while the
    # house wants heat anyway: adopt HIGH, do not start yet another two-hour hold.
    d = decide(_observed(clock, HIGH, 130, hold_for=-1, setpoint=LOW))

    assert d.boiler_hold_until is None
    assert d.boiler_setpoint == HIGH


def test_adopted_hand_value_is_lowered_as_soon_as_demand_ends(clock):
    from dataclasses import replace

    adopted = decide(_observed(clock, HIGH, 130, hold_for=-1, setpoint=LOW))
    cmds = held(clock, adopted.boiler_setpoint, 130)
    inp = replace(make_input(clock, {"office": 19.6, "bedroom": 19.6}, cmds), boiler_observed=HIGH)

    d = decide(inp)

    assert d.boiler_setpoint == LOW and d.boiler_hold_until is None
