from custom_components.smart_heating.dashboard import (
    build_dashboard,
    entity_id,
    slug,
    to_yaml,
)

ROOMS = ["Living Room", "Work room"]


def all_entities(node):
    if isinstance(node, dict):
        for k, v in node.items():
            if k == "entity" and isinstance(v, str):
                yield v
            yield from all_entities(v)
    elif isinstance(node, list):
        for v in node:
            yield from all_entities(v)


def test_slug_and_entity_ids():
    assert slug("Living Room (left)") == "living_room_left"
    assert entity_id("climate", "Work room") == "climate.smart_heating_work_room"
    assert entity_id("sensor", "Work room", "reason") == "sensor.smart_heating_work_room_reason"
    assert entity_id("switch", None, "vacation_mode") == "switch.smart_heating_vacation_mode"


def test_dashboard_has_per_room_status_and_boost():
    cards = [c for v in build_dashboard(ROOMS)["views"] for c in v["cards"]]
    ents = set(all_entities(cards))
    for room in ROOMS:
        assert entity_id("climate", room) in ents
        assert entity_id("sensor", room, "reason") in ents
        assert entity_id("sensor", room, "next_change") in ents
        assert entity_id("sensor", room, "lead_time") in ents
        assert entity_id("button", room, "boost") in ents
        assert entity_id("button", room, "cancel_boost") in ents


def test_dashboard_has_vacation_manual_override_and_options_link():
    d = build_dashboard(ROOMS)
    ents = set(all_entities(d))
    assert {
        "switch.smart_heating_vacation_mode",
        "number.smart_heating_vacation_days",
        "button.smart_heating_manual_room_override",
        "button.smart_heating_cancel_manual_room_override",
    } <= ents
    assert "/config/integrations/integration/smart_heating" in str(d)


def test_yaml_rendering():
    text = to_yaml({"title": "A: b", "n": [1, {"x": None, "y": True}], "e": []})
    assert text == (
        'title: "A: b"\n'
        "n:\n"
        "  - 1\n"
        "  - x: null\n"
        "    y: true\n"
        "e: []\n"
    )


def test_dashboard_explains_every_reason():
    from typing import get_args

    from custom_components.smart_heating.engine.models import Reason

    text = str(build_dashboard(ROOMS))
    for reason in get_args(Reason):
        assert f"| {reason} |" in text
