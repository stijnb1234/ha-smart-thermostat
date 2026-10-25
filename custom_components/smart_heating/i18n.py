"""Pure translations of the texts Smart Heating generates itself (English and Dutch).

The options flow uses Home Assistant's own translation files (strings.json,
translations/*.json); everything else (sentences on cards, alerts, the dashboard,
the weekly report, entity names) comes from here. No Home Assistant imports.
"""

from __future__ import annotations

from typing import Any

DEFAULT_LANGUAGE = "en"
LANGUAGES = ("en", "nl")


def pick_language(code: str | None) -> str:
    """Our language for a Home Assistant language code such as 'nl' or 'nl-NL'."""
    base = (code or "").lower().replace("_", "-").split("-")[0]
    return base if base in LANGUAGES else DEFAULT_LANGUAGE


def number(value: float, lang: str = DEFAULT_LANGUAGE) -> str:
    """19.5 as '19.5' (en) or '19,5' (nl); whole numbers without decimals."""
    text = f"{value:g}"
    return text.replace(".", ",") if lang == "nl" else text


def tr(lang: str, key: str, **params: Any) -> str:
    """The text for `key` in `lang`, English when missing, the key itself as last resort."""
    text = CATALOG.get(lang, {}).get(key)
    if text is None:
        text = CATALOG[DEFAULT_LANGUAGE].get(key, key)
    return text.format(**params) if params else text


WEEKDAYS = {
    "en": ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"),
    "nl": ("ma", "di", "wo", "do", "vr", "za", "zo"),
}


def weekday(lang: str, index: int) -> str:
    return WEEKDAYS.get(lang, WEEKDAYS[DEFAULT_LANGUAGE])[index]


HELP: dict[str, list[tuple[str, str]]] = {
    "en": [
        (
            "Overview",
            "Top line: which rooms heat and whether the boiler is on. Each room shows its "
            "temperature now, what it aims for and what it is doing. Alerts only appear when "
            "something needs attention.\n\nA room can heat while the boiler is off: only rooms "
            "that should be warm call the boiler.",
        ),
        (
            "What a room sentence means",
            "| You see | Meaning |\n|---|---|\n"
            "| Warm until 17:00 | In a scheduled warm period. |\n"
            "| Warm from 08:00 | Lower temperature now, warms up for the next period. |\n"
            "| Kept at 16 degrees | Lower temperature, nothing scheduled. |\n"
            "| Warming up, warm until 17:00 | Started early so it is warm when the schedule begins. |\n"
            "| Boost until 14:00 | You pressed Boost. Warm until then or until you cancel. |\n"
            "| Window seems open, heating paused until 14:20 | It cooled very fast, so heating pauses a while. |\n"
            "| Nobody home, kept at 16 degrees | Nobody is home. Long absence: just above freezing. |\n"
            "| Room's person is away, kept at 16 degrees | The person this room is for is away: schedule skipped. Warms up when they are back or on their way. |\n"
            "| Waiting for the floor heating to warm up first, kept at 12 degrees | The slow floor heating warms up first. Idle radiators stay closed meanwhile. |\n"
            "| Set by hand to 22 degrees, until 17:00 | You turned the valve yourself. Left alone until the room's target changes. The boiler is called if the room is colder than you set. |\n"
            "| Vacation until Mon 00:00, kept at 12 degrees | Vacation mode: just above freezing. The house warms up before you return. |\n\n"
            "Strongest rule wins: Boost, open window, Vacation, nobody home, schedule.",
        ),
        (
            "Heating page",
            "- **Right now / Next change**: what the room does and when that changes.\n"
            "- **Pre-heat lead time**: how early the room starts warming up. A fixed guess at first, "
            "then learned per room.\n"
            "- **Boost / Cancel boost**: warm the room now for a set time, or stop early.\n"
            "- **Radiator valve**: battery and valve details.",
        ),
        (
            "Boiler page",
            "- **Boiler is being called**: only when a room that should be warm is clearly too cold.\n"
            "- **Rooms asking for heat**: who caused the call.\n"
            "- **Target we set / Last sent / Result**: what we told the EasyControl, when, and if it worked.\n"
            "- **Paused after an error**: a short wait so the Bosch cloud is not flooded.\n"
            "- **Manual change on the EasyControl**: you changed it yourself. Respected for about two hours.\n"
            "- **Manual room override**: for rooms you heat by hand. Calls the boiler for a set time. Cancel to stop early.",
        ),
        (
            "Changed something by hand?",
            "A radiator you turn by hand is left alone until that room's target next changes.",
        ),
    ],
    "nl": [
        (
            "Overzicht",
            "Bovenste regel: welke ruimtes verwarmen en of de boiler aan staat. Elke ruimte toont "
            "de temperatuur nu, het doel en wat ze doet. Meldingen verschijnen alleen als er "
            "aandacht nodig is.\n\nEen ruimte kan verwarmen terwijl de boiler uit staat: alleen "
            "ruimtes die warm moeten zijn vragen de boiler om warmte.",
        ),
        (
            "Wat een zin bij een ruimte betekent",
            "| Je ziet | Betekenis |\n|---|---|\n"
            "| Warm tot 17:00 | In een geplande warme periode. |\n"
            "| Warm vanaf 08:00 | Nu lagere temperatuur, warmt op voor de volgende periode. |\n"
            "| Op 16 graden gehouden | Lagere temperatuur, niets gepland. |\n"
            "| Opwarmen, warm tot 17:00 | Eerder begonnen, zodat het warm is als het schema start. |\n"
            "| Boost tot 14:00 | Je drukte op Boost. Warm tot dan of tot je annuleert. |\n"
            "| Raam lijkt open, verwarming gepauzeerd tot 14:20 | Koelde heel snel af, dus de verwarming pauzeert even. |\n"
            "| Niemand thuis, op 16 graden gehouden | Niemand is thuis. Lange afwezigheid: net boven vorst. |\n"
            "| Persoon van deze ruimte is weg, op 16 graden gehouden | De persoon voor wie deze ruimte is, is weg: schema overgeslagen. Warmt op als diegene terug of onderweg is. |\n"
            "| Wacht tot de vloerverwarming is opgewarmd, op 12 graden gehouden | De trage vloerverwarming warmt eerst op. Ongebruikte radiatoren blijven intussen dicht. |\n"
            "| Handmatig ingesteld op 22 graden, tot 17:00 | Je draaide de kraan zelf. Met rust gelaten tot het doel van de ruimte verandert. De boiler wordt gevraagd als de ruimte kouder is dan jouw instelling. |\n"
            "| Vakantie tot ma 00:00, op 12 graden gehouden | Vakantiemodus: net boven vorst. Het huis warmt op voor je terugkomt. |\n\n"
            "Sterkste regel wint: Boost, open raam, Vakantie, niemand thuis, schema.",
        ),
        (
            "Pagina Verwarming",
            "- **Nu / Volgende wijziging**: wat de ruimte doet en wanneer dat verandert.\n"
            "- **Voorverwarmtijd**: hoe vroeg de ruimte begint op te warmen. Eerst een vaste schatting, "
            "daarna per ruimte geleerd.\n"
            "- **Boost / Boost annuleren**: warm de ruimte nu een ingestelde tijd op, of stop eerder.\n"
            "- **Radiatorkraan**: batterij en kraandetails.",
        ),
        (
            "Pagina Boiler",
            "- **Boiler wordt aangeroepen**: alleen als een ruimte die warm moet zijn duidelijk te koud is.\n"
            "- **Ruimtes die warmte vragen**: wie de aanvraag veroorzaakte.\n"
            "- **Doel / Laatst verstuurd / Resultaat**: wat we de EasyControl opdroegen, wanneer, en of het lukte.\n"
            "- **Gepauzeerd na een fout**: even wachten zodat de Bosch-cloud niet overspoeld wordt.\n"
            "- **Handmatige wijziging op de EasyControl**: je veranderde het zelf. Ongeveer twee uur gerespecteerd.\n"
            "- **Handmatige ruimte-override**: voor ruimtes die je met de hand verwarmt. Roept de boiler een ingestelde tijd aan. Annuleer om eerder te stoppen.",
        ),
        (
            "Zelf iets versteld?",
            "Een radiator die je met de hand verstelt, wordt met rust gelaten tot het doel van die ruimte weer verandert.",
        ),
    ],
}


def help_cards(lang: str) -> list[tuple[str, str]]:
    return HELP.get(lang, HELP[DEFAULT_LANGUAGE])


CATALOG: dict[str, dict[str, str]] = {
    "en": {
        # status line and boiler card
        "status.heating": "Heating: {rooms}.",
        "status.nothing": "Nothing is heating.",
        "status.boiler_on": "Boiler on.",
        "status.boiler_off": "Boiler off.",
        "status.vacation": "Vacation mode is on.",
        "status.away": "Nobody is home.",
        "demand.none": "None",
        "demand.manual_override": "Manual room override",
        "backoff.no": "No",
        "backoff.waiting": "Waiting until {at}",
        "hold.no": "No",
        "hold.respecting": "Respecting a manual change until {at}",
        # alerts
        "alert.a_room": "a room",
        "alert.bosch_outage": (
            "The Bosch cloud cannot be reached, so the boiler cannot be called reliably. "
            "The radiator valves keep following the schedule."
        ),
        "alert.trv_offline": "The radiator valve in {room} is not responding.",
        "alert.trv_off": "The radiator valve in {room} is switched off and does not turn back on.",
        "alert.trv_write_failed": "The radiator valve in {room} does not accept its temperature.",
        "alert.low_battery": "The battery of the radiator valve in {room} is low. Replace it soon.",
        "alert.sensor_stale": "The temperature sensor in {room} stopped reporting.",
        "alert.target_not_reached": "{room} has been too cold for a long time and is not reaching its target.",
        "alert.not_warming": "{room} keeps asking for heat but is not warming up. A window may be open or the radiator is not working.",
        # room sentences
        "degrees": "{value} degrees",
        "summary.boost": "Boost until {end}",
        "summary.boost_open": "Boost",
        "summary.window": "Window seems open, heating paused until {end}",
        "summary.window_open": "Window seems open",
        "summary.vacation": "Vacation until {end}, kept at {temp}",
        "summary.vacation_open": "Vacation, kept at {temp}",
        "summary.away": "Nobody home, kept at {temp}",
        "summary.occupant_away": "Room's person is away, kept at {temp}",
        "summary.floor_first": "Waiting for the floor heating to warm up first, kept at {temp}",
        "summary.manual": "Set by hand to {temp}, until {end}",
        "summary.manual_open": "Set by hand to {temp}",
        "summary.pre_heat": "Warming up, warm until {end}",
        "summary.pre_heat_open": "Warming up",
        "summary.schedule": "Warm until {end}",
        "summary.schedule_open": "Warm",
        "summary.setback": "Warm from {end}",
        "summary.setback_open": "Kept at {temp}",
        # entity names
        "entity.reason": "{room} heating reason",
        "entity.summary": "{room} summary",
        "entity.next_change": "{room} next change",
        "entity.lead_time": "{room} pre-heat lead time",
        "entity.boost": "{room} boost",
        "entity.cancel_boost": "{room} cancel boost",
        "entity.manual_override": "Manual room override",
        "entity.cancel_manual_override": "Cancel manual room override",
        "entity.status": "Smart Heating status",
        "entity.active_alerts": "Smart Heating active alerts",
        "entity.boiler_demand_rooms": "Smart Heating boiler demand from",
        "entity.boiler_target": "Smart Heating boiler target (EasyControl)",
        "entity.boiler_last_write": "Smart Heating boiler last write",
        "entity.boiler_write_result": "Smart Heating boiler last write result",
        "entity.boiler_backoff": "Smart Heating boiler backoff",
        "entity.boiler_manual_hold": "Smart Heating boiler manual hold",
        "entity.boiler_call": "Smart Heating boiler called",
        "entity.vacation_days": "Vacation days",
        "entity.vacation_mode": "Vacation mode",
        "entity.alerts_unit": "alerts",
        "climate.set_refused": (
            "This target is set by Smart Heating (schedule, Boost, Away, Vacation). "
            "Use Boost, or edit the room's temperatures under Configure."
        ),
        # dashboard
        "dash.title": "Smart Heating",
        "dash.view.overview": "Overview",
        "dash.view.heating": "Heating",
        "dash.view.boiler": "Boiler",
        "dash.view.help": "Help",
        "dash.right_now": "Right now",
        "dash.alerts": "Alerts",
        "dash.controls": "Controls",
        "dash.boiler": "Boiler",
        "dash.last_24h": "Last 24 hours",
        "dash.manual_override": "Manual room override",
        "dash.help_title": "How to read this",
        "dash.next_change": "Next change",
        "dash.lead_time": "Pre-heat lead time",
        "dash.boost": "Boost",
        "dash.cancel_boost": "Cancel boost",
        "dash.radiator_valve": "Radiator valve",
        "dash.battery": "Battery",
        "dash.valve_opening": "Valve opening",
        "dash.valve_demand": "Valve heating demand",
        "dash.boiler_called": "Boiler is being called",
        "dash.demand_rooms": "Rooms asking for heat",
        "dash.target": "Target we set on the EasyControl",
        "dash.last_sent": "Last sent to the EasyControl",
        "dash.write_result": "Result of last send",
        "dash.paused": "Paused after an error",
        "dash.manual_hold": "Manual change on the EasyControl",
        "dash.table.room": "Room",
        "dash.table.now": "Now",
        "dash.table.aiming": "Aiming for",
        "dash.table.what": "What is happening",
        "dash.options_hint": (
            "Edit schedules, comfort and setback per room under "
            "[Smart Heating options]({link}) (Configure, Edit a room)."
        ),
        "dash.header_alerts": (
            "{% if n > 0 %}**{{ n }} alert{{ 's' if n != 1 }}** need attention, see Alerts below."
            "{% else %}No alerts.{% endif %}"
        ),
        # weekly report
        "report.title": "Smart Heating weekly report",
        "report.no_gas": "Gas: no gas data (or no heating degree-days) this week.",
        "report.gas": "Gas: {gas} m3 over {hdd} HDD = {per} m3/HDD",
        "report.no_last_year": " (no data for last year)",
        "report.vs_last_year": " (last year: {last}, {pct}%)",
        "report.heated_hours": "Heated hours:",
        "report.room_hours": "- {room}: {hours} h",
        "report.no_data": "- no data",
        "report.suggestions": "Suggestions:",
        "report.suggestion": "{room}: you often ask for heat on {days} around {time} ({count} times in 4 weeks). Consider adding that to its schedule.",
        "report.issues": "Issues:",
        "report.no_issues": "No issues.",
        "report.still_active": " (still active)",
        "report.resolved": " (resolved)",
        "report.no_gas_meter": "No gas meter configured (Configure > Gas report settings)",
        "report.no_outdoor": "No outdoor temperature sensor configured",
        # room form errors
        "room_error.invalid_time": "invalid time {text}",
        "room_error.invalid_days": "invalid days {text}",
        "room_error.invalid_line": "invalid schedule line {text}",
        "room_error.empty_window": "empty window in {text}",
        "room_error.name_required": "name is required",
        "room_error.floor_needs_sensor": "a floor heating or open-radiator room needs a temperature sensor",
        "room_error.trv_required": "trv entity is required (or mark the room as manual)",
        "room_error.comfort_range": "comfort must be {low}-{high}",
        "room_error.frost_min": "frost hold must be at least {low}",
        "room_error.temp_order": "need frost hold <= setback <= comfort",
        "room_error.out_of_range": "{key} must be {low}-{high}",
        "room_error.duplicate_name": "a room with that name already exists",
        "room_error.duplicate_trv": "that trv entity is already used by another room",
        "room_error.unknown_room": "unknown room {text}",
    },
    "nl": {
        "status.heating": "Verwarmen: {rooms}.",
        "status.nothing": "Er wordt niets verwarmd.",
        "status.boiler_on": "Boiler aan.",
        "status.boiler_off": "Boiler uit.",
        "status.vacation": "Vakantiemodus staat aan.",
        "status.away": "Niemand is thuis.",
        "demand.none": "Geen",
        "demand.manual_override": "Handmatige ruimte-override",
        "backoff.no": "Nee",
        "backoff.waiting": "Wacht tot {at}",
        "hold.no": "Nee",
        "hold.respecting": "Handmatige wijziging gerespecteerd tot {at}",
        "alert.a_room": "een ruimte",
        "alert.bosch_outage": (
            "De Bosch-cloud is onbereikbaar, dus de boiler kan niet betrouwbaar worden aangeroepen. "
            "De radiatorkranen blijven het schema volgen."
        ),
        "alert.trv_offline": "De radiatorkraan in {room} reageert niet.",
        "alert.trv_off": "De radiatorkraan in {room} staat uit en gaat niet weer aan.",
        "alert.trv_write_failed": "De radiatorkraan in {room} neemt zijn temperatuur niet over.",
        "alert.low_battery": "De batterij van de radiatorkraan in {room} is bijna leeg. Vervang hem binnenkort.",
        "alert.sensor_stale": "De temperatuursensor in {room} meldt niets meer.",
        "alert.target_not_reached": "{room} is al lange tijd te koud en haalt zijn doel niet.",
        "alert.not_warming": "{room} vraagt steeds om warmte maar wordt niet warmer. Mogelijk staat een raam open of werkt de radiator niet.",
        "degrees": "{value} graden",
        "summary.boost": "Boost tot {end}",
        "summary.boost_open": "Boost",
        "summary.window": "Raam lijkt open, verwarming gepauzeerd tot {end}",
        "summary.window_open": "Raam lijkt open",
        "summary.vacation": "Vakantie tot {end}, op {temp} gehouden",
        "summary.vacation_open": "Vakantie, op {temp} gehouden",
        "summary.away": "Niemand thuis, op {temp} gehouden",
        "summary.occupant_away": "Persoon van deze ruimte is weg, op {temp} gehouden",
        "summary.floor_first": "Wacht tot de vloerverwarming is opgewarmd, op {temp} gehouden",
        "summary.manual": "Handmatig ingesteld op {temp}, tot {end}",
        "summary.manual_open": "Handmatig ingesteld op {temp}",
        "summary.pre_heat": "Opwarmen, warm tot {end}",
        "summary.pre_heat_open": "Opwarmen",
        "summary.schedule": "Warm tot {end}",
        "summary.schedule_open": "Warm",
        "summary.setback": "Warm vanaf {end}",
        "summary.setback_open": "Op {temp} gehouden",
        "entity.reason": "{room} verwarmingsreden",
        "entity.summary": "{room} samenvatting",
        "entity.next_change": "{room} volgende wijziging",
        "entity.lead_time": "{room} voorverwarmtijd",
        "entity.boost": "{room} boost",
        "entity.cancel_boost": "{room} boost annuleren",
        "entity.manual_override": "Handmatige ruimte-override",
        "entity.cancel_manual_override": "Handmatige ruimte-override annuleren",
        "entity.status": "Smart Heating status",
        "entity.active_alerts": "Smart Heating actieve meldingen",
        "entity.boiler_demand_rooms": "Smart Heating boiler-aanvraag van",
        "entity.boiler_target": "Smart Heating boilerdoel (EasyControl)",
        "entity.boiler_last_write": "Smart Heating boiler laatst verstuurd",
        "entity.boiler_write_result": "Smart Heating boiler resultaat laatste verzending",
        "entity.boiler_backoff": "Smart Heating boiler pauze",
        "entity.boiler_manual_hold": "Smart Heating boiler handmatige wijziging",
        "entity.boiler_call": "Smart Heating boiler aangeroepen",
        "entity.vacation_days": "Vakantiedagen",
        "entity.vacation_mode": "Vakantiemodus",
        "entity.alerts_unit": "meldingen",
        "climate.set_refused": (
            "Dit doel wordt bepaald door Smart Heating (schema, Boost, Afwezig, Vakantie). "
            "Gebruik Boost, of pas de temperaturen van de ruimte aan onder Configureren."
        ),
        "dash.title": "Smart Heating",
        "dash.view.overview": "Overzicht",
        "dash.view.heating": "Verwarming",
        "dash.view.boiler": "Boiler",
        "dash.view.help": "Help",
        "dash.right_now": "Nu",
        "dash.alerts": "Meldingen",
        "dash.controls": "Bediening",
        "dash.boiler": "Boiler",
        "dash.last_24h": "Laatste 24 uur",
        "dash.manual_override": "Handmatige ruimte-override",
        "dash.help_title": "Zo lees je dit",
        "dash.next_change": "Volgende wijziging",
        "dash.lead_time": "Voorverwarmtijd",
        "dash.boost": "Boost",
        "dash.cancel_boost": "Boost annuleren",
        "dash.radiator_valve": "Radiatorkraan",
        "dash.battery": "Batterij",
        "dash.valve_opening": "Kraanstand",
        "dash.valve_demand": "Warmtevraag van de kraan",
        "dash.boiler_called": "Boiler wordt aangeroepen",
        "dash.demand_rooms": "Ruimtes die warmte vragen",
        "dash.target": "Doel dat we op de EasyControl hebben gezet",
        "dash.last_sent": "Laatst naar de EasyControl gestuurd",
        "dash.write_result": "Resultaat laatste verzending",
        "dash.paused": "Gepauzeerd na een fout",
        "dash.manual_hold": "Handmatige wijziging op de EasyControl",
        "dash.table.room": "Ruimte",
        "dash.table.now": "Nu",
        "dash.table.aiming": "Doel",
        "dash.table.what": "Wat gebeurt er",
        "dash.options_hint": (
            "Pas schema's, comfort- en lage temperatuur per ruimte aan onder "
            "[Smart Heating-opties]({link}) (Configureren, Ruimte bewerken)."
        ),
        "dash.header_alerts": (
            "{% if n > 0 %}**{{ n }} {{ 'melding heeft' if n == 1 else 'meldingen hebben' }}** aandacht nodig, zie Meldingen hieronder."
            "{% else %}Geen meldingen.{% endif %}"
        ),
        "report.title": "Smart Heating weekrapport",
        "report.no_gas": "Gas: geen gasgegevens (of geen graaddagen) deze week.",
        "report.gas": "Gas: {gas} m3 over {hdd} graaddagen = {per} m3/graaddag",
        "report.no_last_year": " (geen gegevens van vorig jaar)",
        "report.vs_last_year": " (vorig jaar: {last}, {pct}%)",
        "report.heated_hours": "Verwarmde uren:",
        "report.room_hours": "- {room}: {hours} u",
        "report.no_data": "- geen gegevens",
        "report.suggestions": "Suggesties:",
        "report.suggestion": "{room}: je vraagt vaak om warmte op {days} rond {time} ({count} keer in 4 weken). Overweeg dit aan het schema toe te voegen.",
        "report.issues": "Problemen:",
        "report.no_issues": "Geen problemen.",
        "report.still_active": " (nog actief)",
        "report.resolved": " (opgelost)",
        "report.no_gas_meter": "Geen gasmeter ingesteld (Configureren > Gasrapport-instellingen)",
        "report.no_outdoor": "Geen buitentemperatuursensor ingesteld",
        "room_error.invalid_time": "ongeldige tijd {text}",
        "room_error.invalid_days": "ongeldige dagen {text}",
        "room_error.invalid_line": "ongeldige schemaregel {text}",
        "room_error.empty_window": "leeg tijdvak in {text}",
        "room_error.name_required": "naam is verplicht",
        "room_error.floor_needs_sensor": "een ruimte met vloerverwarming of open radiatoren heeft een temperatuursensor nodig",
        "room_error.trv_required": "radiatorkraan is verplicht (of markeer de ruimte als handmatig)",
        "room_error.comfort_range": "comfort moet {low}-{high} zijn",
        "room_error.frost_min": "vorstbescherming moet minstens {low} zijn",
        "room_error.temp_order": "vorstbescherming <= lage temperatuur <= comfort is vereist",
        "room_error.out_of_range": "{key} moet {low}-{high} zijn",
        "room_error.duplicate_name": "er bestaat al een ruimte met die naam",
        "room_error.duplicate_trv": "die radiatorkraan wordt al door een andere ruimte gebruikt",
        "room_error.unknown_room": "onbekende ruimte {text}",
    },
}
