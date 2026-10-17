from datetime import time, timedelta

import pytest

from custom_components.smart_heating.engine import RoomConfig, ScheduleWindow
from custom_components.smart_heating.rooms import (
    RoomError,
    add_room,
    format_schedule,
    parse_schedule,
    preset_schedule,
    remove_room,
    room_from_form,
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


def test_manual_room_needs_no_trv_and_is_not_controlled_by_the_engine():
    manual = {"name": "Bathroom", "manual": True}
    rooms = add_room([raw()], manual)

    assert [r.name for r in to_engine_rooms(rooms)] == ["Living"]
    assert trv_entities(rooms) == {"Living": "climate.living_trv"}
    add_room(rooms, {"name": "Floor", "manual": True})  # several TRV-less rooms are fine


def test_non_manual_room_still_requires_trv():
    with pytest.raises(RoomError):
        add_room([], {"name": "Bed"})


def test_engine_room_keeps_calibration_lead_time_and_window_settings():
    [room] = to_engine_rooms(
        [raw(trv_offset=-1.5, lead_time_minutes=90, window_detection=False, window_drop=2.0, window_pause_minutes=25)]
    )

    assert room.trv_offset == -1.5
    assert room.lead_time == timedelta(minutes=90)
    assert room.window_detection is False
    assert room.window_drop == 2.0
    assert room.window_pause == timedelta(minutes=25)


def test_engine_room_defaults_for_new_fields_match_engine_defaults():
    [room] = to_engine_rooms([raw()])

    assert room == RoomConfig(name="Living")


def test_presets_give_the_spec_default_schedules():
    living = preset_schedule("living_area")
    assert living == [{"days": [0, 1, 2, 3, 4, 5, 6], "start": "06:00", "end": "23:00"}]
    work = preset_schedule("working_room")
    assert work == [{"days": [0, 2, 4], "start": "08:00", "end": "17:00"}]


def test_bedroom_preset_is_work_hours_plus_configurable_pre_bed_warmup():
    assert preset_schedule("bedroom") == [
        {"days": [0, 2, 4], "start": "08:00", "end": "17:00"},
        {"days": [0, 1, 2, 3, 4, 5, 6], "start": "21:30", "end": "22:30"},
    ]
    custom = preset_schedule("bedroom", pre_bed=("21:00", "22:00"))
    assert custom[1]["start"] == "21:00" and custom[1]["end"] == "22:00"


def test_form_input_without_schedule_text_uses_the_chosen_preset():
    room = room_from_form({"name": "Work", "trv_entity": "climate.w", "preset": "working_room", "schedule_text": ""})

    assert room["schedule"] == preset_schedule("working_room")
    assert "preset" not in room and "schedule_text" not in room


def test_form_schedule_text_wins_over_preset():
    room = room_from_form(
        {"name": "W", "trv_entity": "climate.w", "preset": "bedroom", "schedule_text": "mon 09:00-10:00"}
    )

    assert room["schedule"] == [{"days": [0], "start": "09:00", "end": "10:00"}]


def test_form_without_preset_or_text_has_empty_schedule_and_keeps_false_flags():
    room = room_from_form({"name": "W", "trv_entity": "climate.w", "window_detection": False, "sensor_entity": ""})

    assert room["schedule"] == []
    assert room["window_detection"] is False and "sensor_entity" not in room


def test_form_time_with_seconds_is_accepted():
    assert parse_schedule("daily 21:30:00-22:30:00")[0]["start"] == "21:30"


def test_absent_rooms_only_when_all_known_away():
    from custom_components.smart_heating.rooms import absent_rooms, presence_entities

    rooms = [{"name": "Work", "presence_entities": ["person.a", "person.b"]}, {"name": "Hall"}]
    pres = presence_entities(rooms)
    assert pres == {"Work": ("person.a", "person.b")}
    assert absent_rooms(pres, {"person.a": False, "person.b": False}) == {"Work"}
    assert absent_rooms(pres, {"person.a": False, "person.b": True}) == frozenset()
    assert absent_rooms(pres, {"person.a": False, "person.b": None}) == frozenset()


def test_arrival_signal_cancels_absence():
    from custom_components.smart_heating.rooms import absent_rooms, arrival_entities

    rooms = [{"name": "Work", "presence_entities": ["person.a"], "arrival_entities": ["person.a_near"]}]
    arr = arrival_entities(rooms)
    pres = {"Work": ("person.a",)}
    assert absent_rooms(pres, {"person.a": False}, arr, {"person.a_near": False}) == {"Work"}
    assert absent_rooms(pres, {"person.a": False}, arr, {"person.a_near": True}) == frozenset()


def test_floor_heating_room_needs_sensor_not_trv_and_gets_long_default_lead():
    import pytest

    from custom_components.smart_heating.rooms import RoomError, room_from_form, to_engine_rooms, validate_room

    with pytest.raises(RoomError):
        validate_room({"name": "Bath", "floor_heating": True})
    room = room_from_form({"name": "Bath", "floor_heating": True, "sensor_entity": "sensor.t", "lead_time_minutes": 70})
    validate_room(room)
    (engine_room,) = to_engine_rooms([room])
    assert engine_room.floor_heating and engine_room.lead_time.total_seconds() == 3 * 3600


def test_schedule_accepts_dutch_day_names():
    from custom_components.smart_heating.rooms import parse_schedule

    assert parse_schedule("ma,wo,vr 08:00-17:00")[0]["days"] == [0, 2, 4]
    assert parse_schedule("ma-vr 07:00-09:00")[0]["days"] == [0, 1, 2, 3, 4]
    assert parse_schedule("dagelijks 06:00-23:00")[0]["days"] == list(range(7))


def test_floor_heating_wins_over_manual_flag():
    from custom_components.smart_heating.rooms import room_from_form, to_engine_rooms

    stored = {"name": "Kitchen", "manual": True, "floor_heating": True, "sensor_entity": "sensor.t"}
    assert [r.name for r in to_engine_rooms([stored])] == ["Kitchen"]
    assert "manual" not in room_from_form({**stored, "lead_time_minutes": 180})


def test_zone_arrival_counts_people_in_it():
    from custom_components.smart_heating.presence_adapter import is_arriving

    assert is_arriving("zone.almost_home", "1")
    assert not is_arriving("zone.almost_home", "0")
    assert not is_arriving("zone.almost_home", "unavailable")
    assert is_arriving("person.a", "Almost home")
    assert not is_arriving("person.a", "not_home")
    assert not is_arriving("binary_sensor.near", "off")
    assert not is_arriving("binary_sensor.near", None)
