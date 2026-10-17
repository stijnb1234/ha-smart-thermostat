from datetime import datetime, timedelta, timezone

from custom_components.smart_heating.engine import Commands, commands_from_dict, commands_to_dict

NOW = datetime(2026, 1, 12, 10, 0, tzinfo=timezone.utc)


def sample() -> Commands:
    return Commands(
        trv_setpoints={"work": 19.5, "gone": 16.0},
        trv_written_at={"work": NOW},
        trv_previous={"work": 16.0},
        trv_retries={"work": 1},
        trv_manual={"work": 19.5},
        easycontrol_setpoint=22.0,
        easycontrol_changed_at=NOW - timedelta(minutes=3),
        easycontrol_hold_until=NOW + timedelta(hours=2),
    )


def test_roundtrip_drops_unconfigured_rooms():
    back = commands_from_dict(commands_to_dict(sample()), ["work"])
    assert back.trv_setpoints == {"work": 19.5}
    assert back.trv_written_at == {"work": NOW}
    assert back.trv_manual == {"work": 19.5} and back.trv_retries == {"work": 1}
    assert back.easycontrol_setpoint == 22.0
    assert back.easycontrol_hold_until == NOW + timedelta(hours=2)


def test_bad_or_missing_data_gives_empty_commands():
    assert commands_from_dict(None, ["work"]) == Commands()
    assert commands_from_dict({"version": 99}, ["work"]) == Commands()
    assert commands_from_dict({"version": 1, "trv_written_at": {"work": "nope"}}, ["work"]) == Commands()
