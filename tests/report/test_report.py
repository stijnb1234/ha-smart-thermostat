from datetime import datetime, timedelta

from custom_components.smart_heating.engine import Alert, AlertNotifier
from custom_components.smart_heating.report import (
    alert_issues,
    build_report,
    heated_hours,
    heating_degree_days,
)


def test_hdd_sums_only_days_below_base():
    assert heating_degree_days([10.0, 20.0, 18.0, 16.5], base=18.0) == 9.5


def test_hdd_base_is_configurable():
    assert heating_degree_days([10.0], base=15.0) == 5.0


def test_heated_hours_from_samples():
    t0 = datetime(2026, 10, 12, 6, 0)
    samples = [
        (t0, True),
        (t0 + timedelta(hours=2), False),
        (t0 + timedelta(hours=5), True),
    ]
    end = t0 + timedelta(hours=6)
    assert heated_hours(samples, end) == 3.0


def test_report_compares_m3_per_hdd_with_last_year():
    r = build_report(
        gas_m3=60.0, temps=[8.0] * 6,  # 60 HDD -> 1.0 m3/HDD
        last_gas_m3=90.0, last_temps=[8.0] * 6,  # 1.5 m3/HDD
        room_hours={"Living": 40.5, "Bedroom": 10.0},
        issues=["Bedroom TRV offline"],
    )
    assert r.m3_per_hdd == 1.0
    assert r.last_year_m3_per_hdd == 1.5
    assert round(r.change_pct) == -33
    text = r.format()
    assert "1.00 m3/HDD" in text
    assert "last year: 1.50" in text
    assert "-33%" in text
    assert "Living: 40.5 h" in text
    assert "Bedroom TRV offline" in text


def test_report_handles_missing_last_year():
    r = build_report(gas_m3=60.0, temps=[8.0] * 6, last_gas_m3=None, last_temps=[],
                     room_hours={}, issues=[])
    assert r.last_year_m3_per_hdd is None and r.change_pct is None
    text = r.format()
    assert "no data for last year" in text.lower()
    assert "No issues" in text


def test_report_handles_missing_gas_or_zero_hdd():
    r = build_report(gas_m3=None, temps=[8.0], last_gas_m3=5.0, last_temps=[20.0],
                     room_hours={}, issues=[])
    assert r.m3_per_hdd is None and r.last_year_m3_per_hdd is None
    assert "no gas data" in r.format().lower()


def test_alert_issues_list_recent_and_active_alerts_once():
    t = datetime(2026, 10, 12, 6, 0)
    low = Alert("low_battery", "Bed", "TRV battery in Bed is low")
    outage = Alert("bosch_outage", None, "Bosch cloud unreachable")
    old = Alert("trv_offline", "Old", "TRV in Old is offline")
    history = [(t - timedelta(days=30), old), (t + timedelta(hours=1), outage), (t + timedelta(days=1), low),
               (t + timedelta(days=2), low)]

    lines = alert_issues(history, [low], since=t)

    assert len(lines) == 2
    assert lines[0].startswith("The Bosch cloud cannot be reached") and lines[0].endswith("(resolved)")
    assert lines[1] == "The battery of the radiator valve in Bed is low. Replace it soon. (still active)"
    nl = alert_issues(history, [low], since=t, lang="nl")
    assert nl[1].endswith("(nog actief)") and "Bed" in nl[1]


def test_notifier_records_raise_history_with_time():
    n = AlertNotifier()
    t = datetime(2026, 10, 12, 6, 0)
    a = Alert("low_battery", "Bed", "low")
    n.update((a,), t)
    n.update((a,), t + timedelta(minutes=1))

    assert n.history == [(t, a)] and n.active == (a,)


def test_report_lists_schedule_suggestions_in_both_languages():
    from datetime import time

    from custom_components.smart_heating.engine.insights import Suggestion
    from custom_components.smart_heating.report import suggestion_lines

    s = Suggestion("Study", (0, 2), time(7, 10), 4)
    en, nl = suggestion_lines([s], "en"), suggestion_lines([s], "nl")
    assert "Study" in en[0] and "07:10" in en[0] and "Mon, Wed" in en[0]
    assert "Study" in nl[0] and "ma, wo" in nl[0].lower()
    report = build_report(
        gas_m3=None, temps=[], last_gas_m3=None, last_temps=[], room_hours={}, issues=[], suggestions=en
    )
    assert "Suggestions:" in report.format("en") and en[0] in report.format("en")
