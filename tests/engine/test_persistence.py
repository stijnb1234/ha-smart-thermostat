from datetime import timedelta

from custom_components.smart_heating.engine import (
    Boost,
    ManualRoomOverride,
    timed_requests_from_dict,
    timed_requests_to_dict,
)


def test_active_requests_survive_a_roundtrip(clock):
    boosts = {"bedroom": Boost(clock.now(), timedelta(minutes=60))}
    overrides = {"manual_room": ManualRoomOverride(clock.now(), timedelta(hours=2))}
    data = timed_requests_to_dict(boosts, overrides)

    clock.advance(minutes=30)
    assert timed_requests_from_dict(data, clock.now()) == (boosts, overrides)


def test_expired_requests_are_dropped_on_load(clock):
    boosts = {"bedroom": Boost(clock.now(), timedelta(minutes=60))}
    data = timed_requests_to_dict(boosts, {})

    clock.advance(minutes=61)
    assert timed_requests_from_dict(data, clock.now()) == ({}, {})


def test_missing_or_garbage_data_gives_empty_state(clock):
    assert timed_requests_from_dict(None, clock.now()) == ({}, {})
    junk = {"boosts": {"a": {"start": "nope", "seconds": 1}, "b": {}}, "manual_overrides": 5}
    assert timed_requests_from_dict(junk, clock.now()) == ({}, {})
