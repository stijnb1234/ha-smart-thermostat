"""Smart Heating integration. HA imports stay inside functions so the engine
package can be imported and tested without Home Assistant installed."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from .const import CONF_ROOMS, CONF_Z2M_BASE_TOPIC, DASHBOARD_FILE, DOMAIN
from .dashboard import build_dashboard, to_yaml
from .i18n import pick_language
from .migration import CONFIG_VERSION, migrate_options, migrate_unique_id
from .rooms import (
    RoomKeys,
    arrival_entities,
    is_manual,
    presence_entities,
    sensor_entities,
    to_engine_rooms,
    trv_entities,
)
from .settings import boost_duration, manual_override_duration
from .trv_devices import DEFAULT_Z2M_BASE_TOPIC, TrvDevice

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant, ServiceCall

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["binary_sensor", "button", "climate", "datetime", "sensor", "switch"]
SERVICE_SET_VACATION = "set_vacation"
SERVICE_CANCEL_VACATION = "cancel_vacation"


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Domain services (Boost lives on the Room climate entities, see climate.py)."""
    import voluptuous as vol
    from homeassistant.exceptions import ServiceValidationError
    from homeassistant.helpers import config_validation as cv
    from homeassistant.util import dt as dt_util

    from .vacation_plan import VacationPeriod

    def _state():
        entries = list(hass.data.get(DOMAIN, {}).values())
        if not entries:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="not_loaded")
        return entries[0]["vacation"]

    async def set_vacation(call: ServiceCall) -> None:
        start = dt_util.as_local(call.data.get("start") or dt_util.now())
        end = dt_util.as_local(call.data["end"])
        if end <= max(start, dt_util.now()):
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="return_in_past")
        _state().set_manual(VacationPeriod(start, end))

    async def cancel_vacation(call: ServiceCall) -> None:
        _state().set_manual(None)

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_VACATION,
        set_vacation,
        vol.Schema({vol.Optional("start"): cv.datetime, vol.Required("end"): cv.datetime}),
    )
    hass.services.async_register(DOMAIN, SERVICE_CANCEL_VACATION, cancel_vacation, vol.Schema({}))
    return True


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Version 2: generic boiler option names, stable Room ids, unique ids by Room id."""
    from homeassistant.helpers import entity_registry as er

    if entry.version > CONFIG_VERSION:
        return False
    if entry.version < 2:
        options = migrate_options(entry.options, entry.version)
        rooms = options.get(CONF_ROOMS, [])

        def move(reg_entry: er.RegistryEntry) -> dict[str, Any] | None:
            new = migrate_unique_id(reg_entry.unique_id, entry.entry_id, rooms)
            return {"new_unique_id": new} if new else None

        await er.async_migrate_entries(hass, entry.entry_id, move)
        hass.config_entries.async_update_entry(entry, options=options, version=2)
        _LOGGER.info("Migrated Smart Heating configuration to version 2 (Room ids, generic boiler options)")
    return True


def _discover_trvs(hass: HomeAssistant, rooms: dict[str, str], base_topic: str) -> dict[str, TrvDevice]:
    """What each Room's TRV offers, from the entities on its device (see trv_devices.py)."""
    from homeassistant.helpers import device_registry as dr
    from homeassistant.helpers import entity_registry as er

    from .trv_devices import DeviceEntity, fallback_trv, resolve_trv

    ent_reg, dev_reg = er.async_get(hass), dr.async_get(hass)
    devices: dict[str, TrvDevice] = {}
    for room, climate in rooms.items():
        entry = ent_reg.async_get(climate)
        device = dev_reg.async_get(entry.device_id) if entry and entry.device_id else None
        if device is None:
            devices[room] = fallback_trv(climate, base_topic)
            continue
        siblings = [
            DeviceEntity(
                e.entity_id,
                e.device_class or e.original_device_class,
                e.unit_of_measurement,
                e.original_name or e.translation_key or "",
            )
            for e in er.async_entries_for_device(ent_reg, device.id)
            if e.entity_id != climate and not e.disabled
        ]
        devices[room] = resolve_trv(climate, siblings, device.name, device.identifiers, base_topic)
        _LOGGER.debug("TRV for %s: %s", room, devices[room])
    return devices


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    from homeassistant.const import EVENT_HOMEASSISTANT_STOP
    from homeassistant.util import dt as dt_util

    from . import dashboard_panel
    from .commands_store import CommandsStore
    from .coordinator import Persistence, SmartHeatingCoordinator
    from .insights_store import InsightsStore
    from .learner_store import LearnerStore
    from .override_store import OverrideStore
    from .report_glue import schedule_weekly_report
    from .vacation import VacationState

    rooms = entry.options.get(CONF_ROOMS, [])
    keys = RoomKeys(rooms)
    override_store = OverrideStore(hass, keys)
    boosts, manual_overrides = await override_store.async_load(dt_util.utcnow())
    trv_devices = _discover_trvs(
        hass, trv_entities(rooms), entry.options.get(CONF_Z2M_BASE_TOPIC) or DEFAULT_Z2M_BASE_TOPIC
    )
    shared: dict[str, Any] = {
        "rooms": to_engine_rooms(rooms),
        "sensor_entities": sensor_entities(rooms),
        "presence_entities": presence_entities(rooms),
        "arrival_entities": arrival_entities(rooms),
        "boosts": boosts,
        "manual_overrides": manual_overrides,
        "override_store": override_store,
        "boost_duration": boost_duration(entry.options),
        "manual_override_duration": manual_override_duration(entry.options),
        "vacation": VacationState(),
        "lang": pick_language(hass.config.language),
    }
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = shared
    learner_store, insights_store = LearnerStore(hass, keys), InsightsStore(hass, keys)
    commands_store = CommandsStore(hass, keys)
    restored, away_since = await commands_store.async_load([r["name"] for r in rooms])
    persistence = Persistence(
        learner_store=learner_store,
        learner=await learner_store.async_load(),
        commands_store=commands_store,
        insights_store=insights_store,
        insights=await insights_store.async_load(),
        restored=restored,
        away_since=away_since,
    )
    coordinator = SmartHeatingCoordinator(hass, entry, shared, persistence, trv_devices)
    shared["coordinator"] = coordinator
    shared["vacation"].coordinator = coordinator

    dashboard_rooms = [_dashboard_room(r, trv_devices) for r in rooms if not is_manual(r)]
    await hass.async_add_executor_job(
        _write_dashboard, hass.config.path(DASHBOARD_FILE), dashboard_rooms, shared["lang"]
    )
    if dashboard_panel.register(hass):
        entry.async_on_unload(lambda: dashboard_panel.unregister(hass))

    entry.async_on_unload(schedule_weekly_report(hass, entry))

    async def _flush_on_stop(_event) -> None:
        await coordinator.async_flush()

    entry.async_on_unload(hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, _flush_on_stop))
    # Platforms first: the vacation switch restores its state before the first cycle runs.
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await coordinator.async_refresh()
    # Options changes reload the entry, so edits apply without restarting HA.
    entry.async_on_unload(entry.add_update_listener(_async_reload_on_change))
    return True


def _dashboard_room(room: dict[str, Any], devices: dict[str, TrvDevice]) -> dict[str, Any]:
    device = devices.get(room["name"])
    if device is None:
        return room
    return {
        **room,
        "trv_battery": device.battery,
        "trv_valve_position": device.valve_position,
        "trv_heating_demand": device.heating_demand,
    }


def _write_dashboard(path: str, rooms: list[dict], lang: str) -> None:
    from pathlib import Path

    Path(path).write_text(to_yaml(build_dashboard(rooms, lang)), encoding="utf-8")


async def _async_reload_on_change(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    shared = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    if (coordinator := shared.get("coordinator")) is not None:
        # Learned data waiting for its periodic save would be lost on reload otherwise.
        await coordinator.async_flush()
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return unloaded
