from custom_components.smart_heating.migration import migrate_options, migrate_unique_id


def test_v1_options_get_generic_boiler_keys_and_room_ids():
    v1 = {
        "easycontrol_entity": "climate.ec",
        "easycontrol_low": 15,
        "persons": ["person.a"],
        "rooms": [{"name": "Woonkamer links", "trv_entity": "climate.x"}],
    }
    v2 = migrate_options(v1, 1)
    assert v2["boiler_entity"] == "climate.ec" and v2["boiler_low"] == 15
    assert "easycontrol_entity" not in v2 and v2["persons"] == ["person.a"]
    assert v2["rooms"] == [{"name": "Woonkamer links", "trv_entity": "climate.x", "id": "woonkamer_links"}]


def test_current_options_are_left_alone():
    v2 = {"boiler_entity": "climate.ec", "rooms": [{"name": "A", "id": "x"}]}
    assert migrate_options(v2, 2) == v2


def test_unique_ids_move_from_room_name_to_room_id():
    rooms = [{"name": "Bed", "id": "bed"}, {"name": "Guest_Bed", "id": "guest_bed"}, {"name": "Living room", "id": "living_room"}]
    assert migrate_unique_id("e1_climate_Living room", "e1", rooms) == "e1_climate_living_room"
    assert migrate_unique_id("e1_summary_Guest_Bed", "e1", rooms) == "e1_summary_guest_bed"
    assert migrate_unique_id("e1_boost_Bed", "e1", rooms) == "e1_boost_bed"
    assert migrate_unique_id("e1_boost_bed", "e1", [{"name": "bed", "id": "bed"}]) is None  # already the id
    assert migrate_unique_id("e1_boiler_call", "e1", rooms) is None
    assert migrate_unique_id("other_climate_Living room", "e1", rooms) is None
