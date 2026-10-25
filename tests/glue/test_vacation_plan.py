from datetime import datetime, timedelta, timezone

from custom_components.smart_heating.vacation_plan import (
    VacationPeriod,
    VacationPlanner,
    merge,
    parse_keywords,
    periods_from_events,
)

TZ = timezone(timedelta(hours=1))
NOW = datetime(2026, 7, 10, 12, 0, tzinfo=TZ)


def at(day, hour=0):
    return datetime(2026, 7, day, hour, 0, tzinfo=TZ)


def test_keywords_are_comma_separated_and_blank_means_all():
    assert parse_keywords(" Vacation, vakantie ,") == ("vacation", "vakantie")
    assert parse_keywords("") == ()
    assert parse_keywords("*") == ()


def test_all_day_event_runs_from_local_midnight_to_the_exclusive_end_date():
    events = [{"summary": "Zomervakantie Italië", "start": "2026-07-11", "end": "2026-07-25"}]
    assert periods_from_events(events, ("vakantie",), TZ) == [VacationPeriod(at(11), at(25))]


def test_timed_event_uses_its_exact_return_time():
    events = [{"summary": "Holiday", "start": "2026-07-11T07:00:00+01:00", "end": "2026-07-18T19:30:00+01:00"}]
    [period] = periods_from_events(events, ("holiday",), TZ)
    assert period.end == datetime(2026, 7, 18, 19, 30, tzinfo=TZ)


def test_events_without_a_keyword_are_ignored_unless_no_keywords_are_set():
    events = [{"summary": "Dentist", "start": "2026-07-11T09:00:00+01:00", "end": "2026-07-11T10:00:00+01:00"}]
    assert periods_from_events(events, ("vacation",), TZ) == []
    assert len(periods_from_events(events, (), TZ)) == 1


def test_keyword_in_the_description_counts_and_bad_events_are_skipped():
    events = [
        {"summary": "Trip", "description": "family vacation", "start": "2026-07-11", "end": "2026-07-12"},
        {"summary": "vacation", "start": "garbage", "end": "2026-07-12"},
        {"summary": "vacation", "start": "2026-07-12", "end": "2026-07-11"},
    ]
    assert len(periods_from_events(events, ("vacation",), TZ)) == 1


def test_back_to_back_periods_merge():
    assert merge([VacationPeriod(at(14), at(20)), VacationPeriod(at(11), at(14))]) == [VacationPeriod(at(11), at(20))]


def test_planner_is_active_during_a_period_and_reports_the_return():
    p = VacationPlanner()
    p.calendar = [VacationPeriod(at(9), at(20, 18))]
    assert p.until(NOW, anyone_home=False) == at(20, 18)


def test_planner_ignores_a_period_that_has_not_started():
    p = VacationPlanner()
    p.manual = VacationPeriod(at(12), at(20))
    assert p.until(NOW, anyone_home=True) is None
    assert p.upcoming(NOW) == VacationPeriod(at(12), at(20))


def test_after_the_return_until_stays_set_until_someone_is_home_then_manual_clears():
    p = VacationPlanner()
    p.manual = VacationPeriod(at(1), at(10, 11))
    assert p.until(at(10, 10), anyone_home=False) == at(10, 11)
    assert p.until(NOW, anyone_home=False) == at(10, 11)  # back time passed, nobody home yet
    assert p.until(NOW, anyone_home=True) is None
    assert p.manual is None


def test_manual_and_calendar_overlap_into_one_period():
    p = VacationPlanner()
    p.calendar = [VacationPeriod(at(5), at(12))]
    p.manual = VacationPeriod(at(11), at(15))
    assert p.until(NOW, anyone_home=False) == at(15)


def test_period_roundtrip_and_bad_data():
    period = VacationPeriod(at(1), at(5))
    assert VacationPeriod.from_dict(period.to_dict()) == period
    assert VacationPeriod.from_dict({"start": "x"}) is None
    assert VacationPeriod.from_dict(None) is None
