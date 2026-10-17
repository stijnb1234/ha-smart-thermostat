from custom_components.smart_heating.dashboard import (
    build_dashboard,
    entity_id,
    slug,
    to_yaml,
)

ROOMS = [
    {"name": "Living Room", "trv_entity": "climate.trv_living"},
    {"name": "Work room", "trv_entity": "climate.trv_work"},
]
NAMES = [r["name"] for r in ROOMS]


def view(d, path):
    return next(v for v in d["views"] if v["path"] == path)


def cards_of(v):
    if "sections" in v:
        return [c for sec in v["sections"] for c in sec["cards"]]
    return v["cards"]



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


def test_views_are_overview_heating_boiler_help():
    assert [v["path"] for v in build_dashboard(ROOMS)["views"]] == [
        "overview", "heating", "boiler", "help"
    ]


def test_rooms_view_has_one_section_per_room_with_entities_and_graph():
    rooms_view = view(build_dashboard(ROOMS), "heating")
    assert len(rooms_view["sections"]) == len(ROOMS)
    for room, section in zip(NAMES, rooms_view["sections"]):
        ents = set(all_entities(section))
        for ent in (
            entity_id("climate", room),
            entity_id("sensor", room, "summary"),
            entity_id("sensor", room, "next_change"),
            entity_id("sensor", room, "lead_time"),
            entity_id("button", room, "boost"),
            entity_id("button", room, "cancel_boost"),
        ):
            assert ent in ents
        assert entity_id("sensor", room, "reason") not in ents  # raw reason is not shown
        graphs = [c for c in section["cards"] if c["type"] == "history-graph"]
        assert graphs and graphs[0]["hours_to_show"] == 24


def test_trv_technical_entities_derived_from_trv_entity():
    section = view(build_dashboard(ROOMS), "heating")["sections"][1]
    ents = set(all_entities(section))
    assert {
        "sensor.trv_work_battery",
        "number.trv_work_valve_position",
        "sensor.trv_work_pi_heating_demand",
    } <= ents


def test_room_without_trv_has_no_technical_card_and_names_still_work():
    d = build_dashboard(["Hall", {"name": "Study"}])
    ents = set(all_entities(d))
    assert entity_id("climate", "Hall") in ents and entity_id("climate", "Study") in ents
    assert not any("battery" in e for e in ents)


def test_boiler_view_has_details_and_history():
    ents = set(all_entities(view(build_dashboard(ROOMS), "boiler")))
    assert {
        "binary_sensor.smart_heating_boiler_call",
        "sensor.smart_heating_boiler_demand_rooms",
        "sensor.smart_heating_boiler_target",
        "sensor.smart_heating_boiler_last_write",
        "sensor.smart_heating_boiler_write_result",
        "sensor.smart_heating_boiler_backoff",
    } <= ents


def test_overview_has_status_rooms_alerts_controls_but_no_technical_boiler_details():
    ov = view(build_dashboard(ROOMS), "overview")
    text = str(ov)
    assert "boiler_write_result" not in text and "boiler_backoff" not in text
    for room in NAMES:
        assert entity_id("climate", room) in text and entity_id("sensor", room, "summary") in text
    assert "sensor.smart_heating_status" in text
    assert "sensor.smart_heating_active_alerts" in text


def test_alerts_card_only_shown_when_alerts_exist():
    cards = cards_of(view(build_dashboard(ROOMS), "overview"))
    cond = [c for c in cards if c["type"] == "conditional"]
    assert len(cond) == 1
    assert cond[0]["conditions"] == [
        {"entity": "sensor.smart_heating_active_alerts", "state_not": "0"}
    ]


def test_only_standard_cards():
    allowed = {
        "entities", "markdown", "glance", "tile", "grid", "history-graph",
        "conditional", "vertical-stack", "horizontal-stack", "heading", "sections",
    }

    def types(node):
        if isinstance(node, dict):
            if "type" in node:
                yield node["type"]
            for v in node.values():
                yield from types(v)
        elif isinstance(node, list):
            for v in node:
                yield from types(v)

    assert set(types(build_dashboard(ROOMS))) <= allowed


def test_overview_keeps_controls():
    ents = set(all_entities(view(build_dashboard(ROOMS), "overview")))
    assert {
        "switch.smart_heating_vacation_mode",
        "number.smart_heating_vacation_days",
        "button.smart_heating_manual_room_override",
    } <= ents


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


def test_help_explains_every_sentence_the_rooms_can_show():
    from datetime import datetime, timezone
    from typing import get_args

    from custom_components.smart_heating.engine.models import Reason
    from custom_components.smart_heating.explain import Explanation, summarize

    help_text = str(view(build_dashboard(ROOMS), "help"))
    now = datetime(2026, 1, 12, 10, 0, tzinfo=timezone.utc)
    for reason in get_args(Reason):
        sentence = summarize(Explanation(reason, 16.0, now, 19.5), now)
        stem = sentence.split("10:00")[0].split("16 degrees")[0].strip(" ,")
        assert stem.split(" until")[0].split(" from")[0] in help_text, sentence
