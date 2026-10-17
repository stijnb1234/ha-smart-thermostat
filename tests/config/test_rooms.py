from datetime import time

import pytest

from custom_components.smart_heating.engine import RoomConfig, ScheduleWindow
from custom_components.smart_heating.rooms import (
    RoomError,
    add_room,
    format_schedule,
    parse_schedule,
    remove_room,
    replace_room,
    sensor_entities,
    to_engine_rooms,
    trv_entities,
)


def raw(**kw):
    base = {"name": "Living", "trv_entity": "climate.living_trv"}
    base.update(kw)
    return base


def test_stored_room_maps_to_engine_room_config_with_defaults():
    [room] = to_engine_rooms([raw()])
    assert room == RoomConfig(name="Living", comfort=19.5, setback=16.0, frost_hold=12.0, schedule=())


def test_stored_room_values_and_schedule_map_to_engine():
    stored = raw(
        comfort=20,
        setback=17,
        frost_hold=10,
        sensor_entity="sensor.living_temp",
        schedule=[{"days": [0, 2, 4], "start": "08:00", "end": "17:00"}],
    )
    [room] = to_engine_rooms([stored])
    assert room == RoomConfig(
        "Living", 20.0, 17.0, 10.0, (ScheduleWindow(frozenset({0, 2, 4}), time(8), time(17)),)
    )


def test_entity_mappings_are_keyed_by_room_name():
    rooms = [raw(), raw(name="Bed", trv_entity="climate.bed", sensor_entity="sensor.bed")]
    assert trv_entities(rooms) == {"Living": "climate.living_trv", "Bed": "climate.bed"}
    assert sensor_entities(rooms) == {"Bed": "sensor.bed"}


def test_schedule_text_roundtrip():
    text = "mon,wed,fri 08:00-17:00\ndaily 06:00-23:00"
    windows = parse_schedule(text)
    assert windows == [
        {"days": [0, 2, 4], "start": "08:00", "end": "17:00"},
        {"days": [0, 1, 2, 3, 4, 5, 6], "start": "06:00", "end": "23:00"},
    ]
    assert format_schedule(windows) == text


def test_schedule_text_ranges_and_blank_lines():
    assert parse_schedule("\nmon-fri 07:30-09:00\n") == [
        {"days": [0, 1, 2, 3, 4], "start": "07:30", "end": "09:00"}
    ]
    assert parse_schedule("") == []


@pytest.mark.parametrize("bad", ["funday 08:00-09:00", "mon 25:00-26:00", "mon 08:00", "mon 08:00-08:00"])
def test_bad_schedule_text_rejected(bad):
    with pytest.raises(RoomError):
        parse_schedule(bad)


def test_add_room_appends_without_mutating():
    existing = [raw()]
    result = add_room(existing, raw(name="Bed", trv_entity="climate.bed"))
    assert [r["name"] for r in result] == ["Living", "Bed"]
    assert len(existing) == 1


def test_duplicate_name_rejected():
    with pytest.raises(RoomError, match="name"):
        add_room([raw()], raw(trv_entity="climate.other"))


def test_same_trv_for_two_rooms_rejected():
    with pytest.raises(RoomError, match="trv"):
        add_room([raw()], raw(name="Bed"))


@pytest.mark.parametrize(
    "kw",
    [
        {"name": " "},
        {"trv_entity": ""},
        {"comfort": 16, "setback": 17},
        {"setback": 11, "frost_hold": 12},
        {"comfort": 40},
        {"frost_hold": 2},
    ],
)
def test_invalid_room_rejected(kw):
    with pytest.raises(RoomError):
        add_room([], raw(**kw))


def test_replace_room_edits_in_place_and_allows_rename():
    rooms = [raw(), raw(name="Bed", trv_entity="climate.bed")]
    result = replace_room(rooms, "Bed", raw(name="Bedroom", trv_entity="climate.bed", comfort=18))
    assert [r["name"] for r in result] == ["Living", "Bedroom"]
    assert result[1]["comfort"] == 18


def test_replace_room_may_keep_own_name_and_trv():
    result = replace_room([raw()], "Living", raw(comfort=21))
    assert result[0]["comfort"] == 21


def test_replace_unknown_room_rejected():
    with pytest.raises(RoomError):
        replace_room([raw()], "Nope", raw())


def test_remove_room():
    rooms = [raw(), raw(name="Bed", trv_entity="climate.bed")]
    assert [r["name"] for r in remove_room(rooms, "Living")] == ["Bed"]
    with pytest.raises(RoomError):
        remove_room(rooms, "Nope")
