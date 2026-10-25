from datetime import UTC, datetime, timedelta

from custom_components.smart_heating.engine import Commands, commands_from_dict, commands_to_dict

NOW = datetime(2026, 1, 12, 10, 0, tzinfo=UTC)


def sample() -> Commands:
    return Commands(
        trv_setpoints={"work": 19.5, "gone": 16.0},
        trv_written_at={"work": NOW},
        trv_previous={"work": 16.0},
        trv_retries={"work": 1},
        trv_manual={"work": 19.5},
        boiler_setpoint=22.0,
        boiler_changed_at=NOW - timedelta(minutes=3),
        boiler_hold_until=NOW + timedelta(hours=2),
    )


def test_roundtrip_drops_unconfigured_rooms():
    back = commands_from_dict(commands_to_dict(sample()), ["work"])
    assert back.trv_setpoints == {"work": 19.5}
    assert back.trv_written_at == {"work": NOW}
    assert back.trv_manual == {"work": 19.5} and back.trv_retries == {"work": 1}
    assert back.boiler_setpoint == 22.0
    assert back.boiler_hold_until == NOW + timedelta(hours=2)


def test_bad_or_missing_data_gives_empty_commands():
    assert commands_from_dict(None, ["work"]) == Commands()
    assert commands_from_dict({"version": 99}, ["work"]) == Commands()
    assert commands_from_dict({"version": 1, "trv_written_at": {"work": "nope"}}, ["work"]) == Commands()


def test_malformed_section_gives_empty_commands_instead_of_crashing():
    assert commands_from_dict({"version": 2, "trv_setpoints": ["work", 19.5]}, ["work"]) == Commands()


def test_data_saved_before_the_boiler_rename_is_read():
    v1 = {
        "version": 1,
        "trv_setpoints": {"work": 19.5},
        "easycontrol_setpoint": 22.0,
        "easycontrol_changed_at": NOW.isoformat(),
        "easycontrol_hold_until": None,
    }
    back = commands_from_dict(v1, ["work"])
    assert back.boiler_setpoint == 22.0 and back.boiler_changed_at == NOW
    assert back.trv_setpoints == {"work": 19.5}


def test_away_since_is_saved_alongside_the_commands():
    from custom_components.smart_heating.engine.state import away_since_from_dict

    data = commands_to_dict(sample(), away_since=NOW)
    assert away_since_from_dict(data) == NOW
    assert away_since_from_dict(commands_to_dict(sample())) is None
    assert away_since_from_dict({"away_since": "garbage"}) is None
    assert away_since_from_dict(None) is None
