from datetime import datetime, timezone

from custom_components.smart_heating.explain import Explanation, summarize

UTC = timezone.utc
NOW = datetime(2026, 1, 12, 10, 0, tzinfo=UTC)
LATER = datetime(2026, 1, 12, 14, 30, tzinfo=UTC)
TOMORROW = datetime(2026, 1, 13, 8, 0, tzinfo=UTC)  # a Tuesday


def test_boost():
    assert summarize(Explanation("boost", 20.0, LATER, 16.0), NOW) == "Boost until 14:30"


def test_window():
    assert summarize(Explanation("window", 12.0, LATER, 20.0), NOW) == (
        "Window seems open, heating paused until 14:30"
    )


def test_schedule_warm_until():
    assert summarize(Explanation("schedule", 20.0, LATER, 16.0), NOW) == "Warm until 14:30"


def test_setback_warm_from():
    assert summarize(Explanation("setback", 16.0, LATER, 20.0), NOW) == "Warm from 14:30"
    assert summarize(Explanation("setback", 16.0, TOMORROW, 20.0), NOW) == "Warm from Tue 08:00"
    assert summarize(Explanation("setback", 16.0), NOW) == "Kept at 16 degrees"


def test_pre_heat():
    assert summarize(Explanation("pre_heat", 20.0, LATER, 16.0), NOW) == (
        "Warming up, warm until 14:30"
    )


def test_vacation_and_away():
    assert summarize(Explanation("vacation", 12.0, TOMORROW, 20.0), NOW) == (
        "Vacation until Tue 08:00, kept at 12 degrees"
    )
    assert summarize(Explanation("away", 16.0), NOW) == "Nobody home, kept at 16 degrees"
    assert summarize(Explanation("away", 16.5), NOW) == "Nobody home, kept at 16.5 degrees"

