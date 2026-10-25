from datetime import timedelta

from custom_components.smart_heating.engine.learner import (
    MIN_SAMPLES,
    SCHEMA_VERSION,
    LeadTimeLearner,
)


def feed(learner, room, outdoor, delta, minutes, n=MIN_SAMPLES):
    for _ in range(n):
        learner.record_warmup(room, outdoor, delta, timedelta(minutes=minutes))


def test_no_estimate_without_enough_samples():
    learner = LeadTimeLearner()
    feed(learner, "bedroom", 5.0, 3.0, 45, n=MIN_SAMPLES - 1)
    assert learner.estimate("bedroom", 5.0, 3.0) is None
    assert learner.lead_times(5.0, {"bedroom": 3.0}) == {}


def test_estimate_after_enough_samples():
    learner = LeadTimeLearner()
    feed(learner, "bedroom", 5.0, 3.0, 45)  # 4 K/h
    assert learner.estimate("bedroom", 5.0, 3.0) == timedelta(minutes=45)
    assert learner.estimate("bedroom", 5.0, 2.0) == timedelta(minutes=30)
    assert learner.lead_times(5.0, {"bedroom": 3.0}) == {
        "bedroom": timedelta(minutes=45)
    }


def test_colder_outdoor_gives_longer_lead_time():
    learner = LeadTimeLearner()
    feed(learner, "bedroom", 0.0, 3.0, 90, n=3)  # 2 K/h
    feed(learner, "bedroom", 10.0, 3.0, 45, n=3)  # 4 K/h
    assert learner.estimate("bedroom", 0.0, 3.0) == timedelta(minutes=90)
    assert learner.estimate("bedroom", 10.0, 3.0) == timedelta(minutes=45)


def test_rooms_learn_independently():
    learner = LeadTimeLearner()
    feed(learner, "bedroom", 5.0, 3.0, 45)
    assert learner.estimate("kitchen", 5.0, 3.0) is None


def test_invalid_observations_ignored():
    learner = LeadTimeLearner()
    feed(learner, "bedroom", 5.0, 0.0, 45)
    feed(learner, "bedroom", 5.0, 3.0, 0)
    assert learner.estimate("bedroom", 5.0, 3.0) is None


def test_estimate_is_clamped():
    learner = LeadTimeLearner()
    feed(learner, "bedroom", 5.0, 0.1, 600)  # absurdly slow
    assert learner.estimate("bedroom", 5.0, 3.0) == timedelta(hours=4)


def test_only_recent_samples_kept():
    learner = LeadTimeLearner()
    feed(learner, "bedroom", 5.0, 3.0, 90, n=50)
    feed(learner, "bedroom", 5.0, 3.0, 45, n=50)
    assert learner.estimate("bedroom", 5.0, 3.0) == timedelta(minutes=45)


def test_round_trip_serialisation():
    learner = LeadTimeLearner()
    feed(learner, "bedroom", 5.0, 3.0, 45)
    data = learner.to_dict()
    assert data["version"] == SCHEMA_VERSION
    restored = LeadTimeLearner.from_dict(data)
    assert restored.estimate("bedroom", 5.0, 3.0) == timedelta(minutes=45)
    assert restored.to_dict() == data


def test_migrates_v1_state():
    # v1 stored samples as [outdoor, rate_k_per_h] pairs.
    v1 = {"version": 1, "rooms": {"bedroom": [[5.0, 4.0]] * MIN_SAMPLES}}
    learner = LeadTimeLearner.from_dict(v1)
    assert learner.estimate("bedroom", 5.0, 3.0) == timedelta(minutes=45)
    assert learner.to_dict()["version"] == SCHEMA_VERSION


def test_unknown_or_missing_state_gives_empty_learner():
    assert LeadTimeLearner.from_dict(None).to_dict()["rooms"] == {}
    assert LeadTimeLearner.from_dict({"version": 999}).to_dict()["rooms"] == {}


def test_estimate_does_not_extrapolate_beyond_the_outdoor_range_seen():
    learner = LeadTimeLearner()
    # Warmer outside -> faster: 1 K/h at 0 degC up to 3 K/h at 8 degC.
    for outdoor, rate in ((0.0, 1.0), (2.0, 1.5), (4.0, 2.0), (6.0, 2.5), (8.0, 3.0)):
        learner.record_warmup("bed", outdoor, delta=rate, duration=timedelta(hours=1))

    # At -20 degC a straight-line fit would predict a negative rate (max lead); held at 0 degC.
    assert learner.estimate("bed", -20.0, 2.0) == learner.estimate("bed", 0.0, 2.0) == timedelta(hours=2)
