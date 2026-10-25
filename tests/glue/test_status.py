from datetime import UTC, datetime, timedelta

from custom_components.smart_heating.engine import (
    Alert,
    Boost,
    Commands,
    EngineConfig,
    EngineInput,
    ManualRoomOverride,
    RoomConfig,
    SensorReading,
    WriteResult,
    decide,
)
from custom_components.smart_heating.status import (
    alert_sentence,
    backoff_text,
    boiler_status,
    demand_text,
    heating_rooms,
    hold_text,
    status_text,
)

UTC = UTC
NOW = datetime(2026, 1, 12, 10, 0, tzinfo=UTC)
LOW, HIGH = 10.0, 22.0


def make(temps, commands=None, last_write=None, boosts=None, overrides=None):
    rooms = tuple(RoomConfig(name=n, comfort=20.0, setback=16.0) for n in temps)
    inp = EngineInput(
        config=EngineConfig(rooms=rooms, boiler_low=LOW, boiler_high=HIGH),
        now=NOW,
        anyone_home=True,
        trv_temps={n: SensorReading(t, NOW) for n, t in temps.items()},
        learned={},
        last_commands=commands or Commands(),
        last_write=last_write,
        boosts={n: Boost(NOW, timedelta(hours=1)) for n in (boosts or [])},
        manual_overrides=overrides or {},
    )
    return inp, decide(inp)


def test_alert_sentences_are_plain_language():
    assert "Work room" in alert_sentence(Alert("trv_offline", "Work room"))
    assert "battery" in alert_sentence(Alert("low_battery", "Hall"))
    assert "Hall" in alert_sentence(Alert("sensor_stale", "Hall"))
    assert "Hall" in alert_sentence(Alert("target_not_reached", "Hall"))
    assert "thermostat" in alert_sentence(Alert("boiler_outage"))
    assert alert_sentence(Alert("weird", None, "raw message")) == "raw message"
    assert alert_sentence(Alert("weird")) == "weird"


def test_heating_rooms_are_those_clearly_below_target():
    inp, d = make({"Work room": 18.0, "Hall": 19.9}, boosts=["Work room", "Hall"])
    assert heating_rooms(inp.config, d.trv_setpoints, d.room_temps) == ("Work room",)


def test_status_text():
    assert status_text(("Work room",), True, False, False) == "Heating: Work room. Boiler on."
    assert status_text(("A", "B"), False, False, False) == "Heating: A, B. Boiler off."
    assert status_text((), False, False, False) == "Nothing is heating. Boiler off."
    assert status_text((), False, True, True) == (
        "Nothing is heating. Boiler off. Vacation mode is on."
    )
    assert status_text((), False, False, True) == "Nothing is heating. Boiler off. Nobody is home."


def test_boiler_status_call_active_follows_setpoint_being_held():
    inp, d = make({"Work room": 18.0}, boosts=["Work room"])
    st = boiler_status(inp, d)  # first write goes out this cycle
    assert (st.call_active, st.demand_rooms, st.held_setpoint) == (True, ("Work room",), HIGH)
    inp, d = make({"Work room": 20.0})
    st = boiler_status(inp, d)
    assert (st.call_active, st.held_setpoint) == (False, LOW)


def test_boiler_status_blocked_write_keeps_held_low():
    held = Commands(boiler_setpoint=LOW, boiler_changed_at=NOW - timedelta(minutes=1))
    inp, d = make({"Work room": 18.0}, commands=held, boosts=["Work room"])
    st = boiler_status(inp, d)
    assert (st.call_active, st.held_setpoint) == (False, LOW)
    assert st.demand_rooms == ("Work room",)  # wants heat, write not yet allowed


def test_boiler_status_last_write_and_backoff():
    failed = WriteResult(at=NOW - timedelta(minutes=1), status="rate_limited", consecutive_failures=1)
    inp, d = make({"Work room": 20.0}, last_write=failed)
    st = boiler_status(inp, d)
    assert st.last_write_result == "rate_limited"
    assert st.last_write_at == failed.at
    assert st.backoff_until == failed.at + timedelta(minutes=5)
    ok = WriteResult(at=NOW, status="ok")
    assert boiler_status(*make({"Work room": 20.0}, last_write=ok)).backoff_until is None
    old = WriteResult(at=NOW - timedelta(hours=2), status="error", consecutive_failures=1)
    assert boiler_status(*make({"Work room": 20.0}, last_write=old)).backoff_until is None
    st = boiler_status(*make({"Work room": 20.0}))
    assert (st.last_write_result, st.last_write_at) == ("none", None)


def test_manual_override_counts_as_demand_source():
    ov = {"manual_room": ManualRoomOverride(NOW, timedelta(hours=1))}
    inp, d = make({"Work room": 20.0}, overrides=ov)
    st = boiler_status(inp, d)
    assert st.manual_override and st.demand_rooms == ()
    assert demand_text(st) == "Manual room override"


def test_demand_and_backoff_text():
    inp, d = make({"A": 18.0, "B": 18.0}, boosts=["A", "B"])
    assert demand_text(boiler_status(inp, d)) == "A, B"
    assert demand_text(boiler_status(*make({"A": 20.0}))) == "None"
    assert backoff_text(None, NOW) == "No"
    assert backoff_text(NOW + timedelta(minutes=5), NOW) == "Waiting until 10:05"


def test_manual_hold_status_and_text():
    held = Commands(
        boiler_setpoint=LOW,
        boiler_changed_at=NOW - timedelta(hours=1),
        boiler_hold_until=NOW + timedelta(minutes=30),
    )
    st = boiler_status(*make({"Work room": 20.0}, commands=held))
    assert st.hold_until == NOW + timedelta(minutes=30)
    assert hold_text(st.hold_until, NOW) == "Respecting a manual change until 10:30"
    assert hold_text(None, NOW) == "No"
    assert boiler_status(*make({"Work room": 20.0})).hold_until is None


def test_room_is_heating_only_while_it_calls_and_the_boiler_call_is_on():
    from dataclasses import replace

    from custom_components.smart_heating.status import room_heating

    inp, decision = make({"office": 17.0})
    calling = replace(decision, demand_rooms=("office",), boiler_setpoint=inp.config.boiler_high)
    assert room_heating("office", inp, calling)
    # Calling, but the boiler write is still held back (debounce): not heating yet.
    held_back = replace(calling, boiler_setpoint=inp.config.boiler_low)
    assert not room_heating("office", inp, held_back)
    assert room_heating("office", inp, held_back, boiler_configured=False)
    # Below target but inside the demand band: not calling, so idle.
    assert not room_heating("office", inp, replace(decision, demand_rooms=()))
