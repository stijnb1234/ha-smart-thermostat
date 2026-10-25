from datetime import UTC, datetime
from typing import get_args

from custom_components.smart_heating.dashboard import build_dashboard
from custom_components.smart_heating.engine import Alert
from custom_components.smart_heating.engine.models import Reason
from custom_components.smart_heating.explain import Explanation, summarize
from custom_components.smart_heating.i18n import CATALOG, number, pick_language, tr
from custom_components.smart_heating.status import alert_sentence, status_text

NOW = datetime(2026, 10, 17, 10, 0, tzinfo=UTC)


def test_pick_language():
    assert [pick_language(c) for c in ("nl", "nl-NL", "NL_be", "en", "de", None)] == [
        "nl", "nl", "nl", "en", "en", "en",
    ]


def test_catalogs_have_the_same_keys():
    assert set(CATALOG["nl"]) == set(CATALOG["en"])


def test_missing_key_falls_back_to_english_then_key():
    assert tr("nl", "no.such.key") == "no.such.key"
    assert tr("xx", "status.nothing") == "Nothing is heating."


def test_dutch_sentences_and_numbers():
    assert number(19.5, "nl") == "19,5" and number(16.0, "nl") == "16"
    e = Explanation("setback", 16.0, datetime(2026, 10, 19, 8, 50, tzinfo=UTC), 19.5)
    assert summarize(e, NOW, "nl") == "Warm vanaf ma 08:50"
    assert summarize(e, NOW, "en") == "Warm from Mon 08:50"
    assert summarize(Explanation("away", 16.5, None), NOW, "nl") == "Niemand thuis, op 16,5 graden gehouden"
    assert status_text(("Werkkamer",), True, False, False, "nl") == "Verwarmen: Werkkamer. Boiler aan."
    assert "Werkkamer" in alert_sentence(Alert("trv_offline", "Werkkamer"), "nl")


def test_every_reason_has_a_dutch_sentence_in_the_dutch_help():
    help_text = str(build_dashboard(["A"], "nl")["views"][3])
    for reason in get_args(Reason):
        sentence = summarize(Explanation(reason, 16.0, NOW, 19.5), NOW, "nl")
        stem = sentence.split("10:00")[0].split("16 graden")[0].strip(" ,")
        assert stem.split(" tot")[0].split(" vanaf")[0] in help_text, sentence


def test_dutch_dashboard_has_dutch_titles_and_overview_keeps_all_controls():
    d = build_dashboard([{"name": "Werkkamer"}], "nl")
    assert [v["title"] for v in d["views"]] == ["Overzicht", "Verwarming", "Boiler", "Help"]
    text = str(d["views"][0])
    for ent in (
        "switch.smart_heating_vacation_mode",
        "datetime.smart_heating_vacation_return",
        "button.smart_heating_manual_room_override",
        "button.smart_heating_cancel_manual_room_override",
        "button.smart_heating_werkkamer_boost",
        "button.smart_heating_werkkamer_cancel_boost",
    ):
        assert ent in text
