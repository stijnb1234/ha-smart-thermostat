"""Thin HA glue for the weekly report: gather data, call report.py, notify.

Unit-tested logic lives in report.py. This file is only verified in a real HA.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from .const import CONF_GAS_ENTITY, CONF_HDD_BASE, CONF_OUTDOOR_ENTITY, CONF_ROOMS, DOMAIN
from .i18n import pick_language, tr
from .report import DEFAULT_HDD_BASE, alert_issues, build_report, heated_hours, suggestion_lines

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

REPORT_WEEKDAY = 0  # Monday
REPORT_HOUR = 8
YEAR_AGO = timedelta(weeks=52)  # whole weeks so weekdays line up


async def _daily_stats(hass, entity_id, start, end, stat_type):
    from homeassistant.components.recorder import get_instance
    from homeassistant.components.recorder.statistics import statistics_during_period

    result = await get_instance(hass).async_add_executor_job(
        statistics_during_period, hass, start, end, {entity_id}, "day", None, {stat_type}
    )
    rows: list[dict] = [dict(row) for row in result.get(entity_id, [])]
    return [row[stat_type] for row in rows if row.get(stat_type) is not None]


async def _gas_and_temps(hass, gas, outdoor, start, end):
    changes = await _daily_stats(hass, gas, start, end, "change") if gas else []
    temps = await _daily_stats(hass, outdoor, start, end, "mean") if outdoor else []
    return (sum(changes) if changes else None), temps


async def _room_hours_and_issues(hass, rooms, start, end):
    from homeassistant.components.recorder import get_instance, history

    hours: dict[str, float] = {}
    issues: list[str] = []
    entities = {room["name"]: room["trv_entity"] for room in rooms if room.get("trv_entity")}
    if not entities:  # Rooms without a TRV (manual, floor heating): no history to report
        return hours, issues
    # hvac_action is an attribute: attribute-only changes must be included, which
    # state_changes_during_period leaves out (it only returns changes of the state itself).
    found = await get_instance(hass).async_add_executor_job(
        lambda: history.get_significant_states(
            hass,
            start,
            end,
            list(entities.values()),
            significant_changes_only=False,
        )
    )
    for name, entity in entities.items():
        states = [s for s in found.get(entity, []) if not isinstance(s, dict)]
        samples = [(max(s.last_updated, start), s.attributes.get("hvac_action") == "heating") for s in states]
        hours[name] = heated_hours(samples, end)
        if any(s.state == "unavailable" for s in states):
            issues.append(f"{name}: TRV was unavailable this week")
    return hours, issues


async def async_send_report(hass: HomeAssistant, entry: ConfigEntry) -> None:
    from homeassistant.util import dt as dt_util

    lang = pick_language(hass.config.language)
    opts = entry.options
    base = float(opts.get(CONF_HDD_BASE, DEFAULT_HDD_BASE))
    end = dt_util.now().replace(minute=0, second=0, microsecond=0)
    start = end - timedelta(days=7)
    gas, outdoor = opts.get(CONF_GAS_ENTITY), opts.get(CONF_OUTDOOR_ENTITY)

    this_gas, temps = await _gas_and_temps(hass, gas, outdoor, start, end)
    last_gas, last_temps = await _gas_and_temps(hass, gas, outdoor, start - YEAR_AGO, end - YEAR_AGO)
    hours, issues = await _room_hours_and_issues(hass, opts.get(CONF_ROOMS, []), start, end)
    coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id, {}).get("coordinator")
    suggestions: list[str] = []
    if coordinator is not None:
        suggestions = suggestion_lines(coordinator.controller.suggestions(dt_util.now()), lang)
        notifier = coordinator.alerts.notifier
        issues += alert_issues(notifier.history, notifier.active, start, lang)
    if not gas:
        issues.append(tr(lang, "report.no_gas_meter"))
    if not outdoor:
        issues.append(tr(lang, "report.no_outdoor"))

    report = build_report(
        gas_m3=this_gas, temps=temps, last_gas_m3=last_gas, last_temps=last_temps,
        room_hours=hours, issues=issues, base=base, suggestions=suggestions,
    )
    await hass.services.async_call(
        "persistent_notification",
        "create",
        {
            "title": tr(lang, "report.title"),
            "message": report.format(lang),
            "notification_id": f"smart_heating_report_{entry.entry_id}",
        },
    )


def schedule_weekly_report(hass: HomeAssistant, entry: ConfigEntry):
    """Fire Mondays 08:00 local time. Returns the unsubscribe callable."""
    from homeassistant.helpers.event import async_track_time_change

    async def _fire(now: datetime) -> None:
        if now.weekday() == REPORT_WEEKDAY:
            await async_send_report(hass, entry)

    return async_track_time_change(hass, _fire, hour=REPORT_HOUR, minute=0, second=0)
