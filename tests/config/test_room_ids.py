"""Stable Room ids: entity ids and learned data survive a rename."""

import pytest

from custom_components.smart_heating.rooms import (
    RoomError,
    RoomKeys,
    add_room,
    ensure_room_ids,
    replace_room,
    slug,
    to_engine_rooms,
)


def raw(**kw):
    base = {"name": "Living", "trv_entity": "climate.living_trv"}
    base.update(kw)
    return base


def test_slug_transliterates_accents_and_drops_punctuation():
    assert slug("Café / Keuken!") == "cafe_keuken"
    assert slug("Woonkamer links") == "woonkamer_links"


def test_new_room_gets_an_id_from_its_name():
    [room] = add_room([], raw(name="Woonkamer links"))
    assert room["id"] == "woonkamer_links"


def test_rename_keeps_the_id():
    rooms = add_room([], raw(name="Bed", trv_entity="climate.bed"))
    [renamed] = replace_room(rooms, "Bed", raw(name="Master bedroom", trv_entity="climate.bed"))
    assert renamed["name"] == "Master bedroom" and renamed["id"] == "bed"


def test_new_room_whose_slug_is_taken_by_a_renamed_room_gets_a_fresh_id():
    rooms = replace_room(add_room([], raw(name="Bed")), "Bed", raw(name="Guest room"))
    rooms = add_room(rooms, raw(name="Bed", trv_entity="climate.other"))
    assert [r["id"] for r in rooms] == ["bed", "bed_2"]


@pytest.mark.parametrize("name", ["living", "LIVING!", "Living "])
def test_names_that_give_the_same_entity_ids_are_rejected(name):
    with pytest.raises(RoomError, match="name"):
        add_room([raw()], raw(name=name, trv_entity="climate.other"))


def test_name_without_letters_or_digits_is_rejected():
    with pytest.raises(RoomError):
        add_room([], raw(name="!!!"))


def test_existing_rooms_without_an_id_get_one_from_their_name():
    rooms = ensure_room_ids([{"name": "Living room"}, {"name": "Bed", "id": "sleep"}])
    assert [r["id"] for r in rooms] == ["living_room", "sleep"]


def test_engine_room_carries_the_id():
    [room] = to_engine_rooms(add_room([], raw(name="Woonkamer")))
    assert room.id == "woonkamer"


def test_room_keys_translate_names_to_ids_and_back():
    keys = RoomKeys([{"name": "Master bedroom", "id": "bed"}, {"name": "Living", "id": "living"}])
    stored = keys.to_ids({"Master bedroom": 1.0, "Living": 2.0, "Gone": 3.0})
    assert stored == {"bed": 1.0, "living": 2.0}
    assert keys.to_names(stored) == {"Master bedroom": 1.0, "Living": 2.0}


def test_room_keys_read_data_saved_by_name_before_ids_existed():
    keys = RoomKeys([{"name": "Living", "id": "living"}])
    assert keys.to_names({"Living": 1.0, "Old room": 2.0}) == {"Living": 1.0}


def test_room_keys_rekey_nested_sections():
    keys = RoomKeys([{"name": "Living", "id": "living"}])
    data = {"version": 1, "drops": {"Living": [0.1]}, "other": {"Living": 5}}
    assert keys.sections_to_ids(data, ("drops",)) == {"version": 1, "drops": {"living": [0.1]}, "other": {"Living": 5}}
    assert keys.sections_to_names({"drops": {"living": [0.1]}}, ("drops",)) == {"drops": {"Living": [0.1]}}
