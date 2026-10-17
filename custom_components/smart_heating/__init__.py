"""Smart Heating integration. HA imports stay inside functions so the engine
package can be imported and tested without Home Assistant installed."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .const import CONF_ROOMS, DOMAIN
from .rooms import sensor_entities, to_engine_rooms, trv_entities

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    rooms = entry.options.get(CONF_ROOMS, [])
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "rooms": to_engine_rooms(rooms),
        "trv_entities": trv_entities(rooms),
        "sensor_entities": sensor_entities(rooms),
    }
    # Options changes reload the entry, so edits apply without restarting HA.
    entry.async_on_unload(entry.add_update_listener(_async_reload_on_change))
    return True


async def _async_reload_on_change(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return True
