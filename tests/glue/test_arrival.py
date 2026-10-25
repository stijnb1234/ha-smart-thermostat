from datetime import UTC, datetime, timedelta

from custom_components.smart_heating.arrival import ArrivalDetector, distance_km

T0 = datetime(2026, 1, 12, 17, 0, tzinfo=UTC)
HOUR = timedelta(hours=1)


def drive(detector, distances, every=timedelta(minutes=3), horizon=HOUR, start=T0, person="person.a"):
    """Feed one fix per `every`; returns whether the person counts as arriving after each."""
    seen = []
    for i, d in enumerate(distances):
        at = start + i * every
        detector.observe(person, at, d, home=False, horizon=horizon)
        seen.append(detector.arriving(person, at))
    return seen


def test_distance_between_two_points():
    # Utrecht Centraal to Amsterdam Centraal, about 35 km as the crow flies.
    assert 33 < distance_km(52.0894, 5.1101, 52.3791, 4.9003) < 37


def test_commuting_home_counts_as_arriving_within_the_horizon():
    # 30 km out at 60 km/h (3 km per 3 minutes): home in about half an hour.
    seen = drive(ArrivalDetector(), [30, 27, 24, 21])
    assert seen == [False, True, True, True]


def test_far_away_but_approaching_waits_until_the_horizon():
    # 300 km out at 100 km/h: arriving only once the ETA drops under one hour.
    distances = [300 - 5 * i for i in range(50)]
    seen = drive(ArrivalDetector(), distances)
    first = seen.index(True)
    assert distances[first] <= 100 and not any(seen[:first])


def test_driving_away_or_jitter_is_not_arriving():
    assert not any(drive(ArrivalDetector(), [10, 13, 16, 19]))
    assert not any(drive(ArrivalDetector(), [10, 10.2, 9.9, 10.1, 9.95]))


def test_turning_away_ends_arriving():
    d = ArrivalDetector()
    assert drive(d, [20, 17, 14])[-1]
    assert not drive(d, [15.5, 17], start=T0 + timedelta(minutes=9))[-1]


def test_stopping_in_traffic_keeps_arriving_for_a_while_then_expires():
    d = ArrivalDetector()
    drive(d, [20, 17, 14])  # last fix at +6 min, ETA about 14 min
    assert d.arriving("person.a", T0 + timedelta(minutes=20))
    assert not d.arriving("person.a", T0 + timedelta(minutes=60))


def test_being_home_clears_it():
    d = ArrivalDetector()
    drive(d, [20, 17, 14])
    d.observe("person.a", T0 + timedelta(minutes=9), 0.0, home=True, horizon=HOUR)
    assert not d.arriving("person.a", T0 + timedelta(minutes=9))


def test_repeated_identical_fix_is_ignored():
    d = ArrivalDetector()
    d.observe("person.a", T0, 20.0, home=False, horizon=HOUR)
    d.observe("person.a", T0, 20.0, home=False, horizon=HOUR)
    assert drive(d, [17, 14], start=T0 + timedelta(minutes=3))[-1]


def test_eta_is_reported_while_arriving():
    d = ArrivalDetector()
    drive(d, [30, 27, 24])
    eta = d.eta("person.a", T0 + timedelta(minutes=6))
    assert eta is not None and timedelta(minutes=20) < eta < timedelta(minutes=30)
