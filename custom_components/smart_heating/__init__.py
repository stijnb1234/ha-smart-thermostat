"""Smart Heating integration. HA imports stay inside functions so the engine
package can be imported and tested without Home Assistant installed."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .const import CONF_ROOMS, DASHBOARD_FILE, DOMAIN
from .dashboard import build_dashboard, to_yaml
from .rooms import sensor_entities, to_engine_rooms, trv_entities
from .settings import boost_duration, manual_override_duration

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant


PLATFORMS = ["button", "climate", "sensor", "number", "switch"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    from .coordinator import SmartHeatingCoordinator
    from homeassistant.util import dt as dt_util

    from .learner_store import LearnerStore
    from .override_store import OverrideStore
    from .vacation import VacationState

    rooms = entry.options.get(CONF_ROOMS, [])
    override_store = OverrideStore(hass)
    boosts, manual_overrides = await override_store.async_load(dt_util.utcnow())
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "rooms": to_engine_rooms(rooms),
        "trv_entities": trv_entities(rooms),
        "sensor_entities": sensor_entities(rooms),
        "boosts": boosts,
        "manual_overrides": manual_overrides,
        "override_store": override_store,
        "boost_duration": boost_duration(entry.options),
        "manual_override_duration": manual_override_duration(entry.options),
        "vacation": VacationState(),
    }
    shared = hass.data[DOMAIN][entry.entry_id]
    learner_store = LearnerStore(hass)
    learner = await learner_store.async_load()
    coordinator = SmartHeatingCoordinator(hass, entry, shared, learner_store, learner)
    shared["coordinator"] = coordinator
    await hass.async_add_executor_job(
        _write_dashboard, hass.config.path(DASHBOARD_FILE), [r.name for r in shared["rooms"]]
    )
    from .report_glue import schedule_weekly_report

    entry.async_on_unload(schedule_weekly_report(hass, entry))
    # Platforms first: the vacation switch restores its state before the first cycle runs.
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await coordinator.async_refresh()
    # Options changes reload the entry, so edits apply without restarting HA.
    entry.async_on_unload(entry.add_update_listener(_async_reload_on_change))
    return True


def _write_dashboard(path: str, rooms: list[str]) -> None:
    from pathlib import Path

    Path(path).write_text(to_yaml(build_dashboard(rooms)), encoding="utf-8")


async def _async_reload_on_change(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return unloaded
