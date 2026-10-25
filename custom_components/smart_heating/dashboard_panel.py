"""Registers the generated dashboard file as a sidebar dashboard.

Mirrors what the lovelace integration does for YAML dashboards declared in
configuration.yaml (see homeassistant/components/lovelace/__init__.py). Those
internals are not a public API, so every failure here is logged and ignored:
the dashboard file is still written and can be registered by hand.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .const import DASHBOARD_FILE

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

URL_PATH = "smart-heating"
TITLE = "Smart Heating"
ICON = "mdi:radiator"


def register(hass: HomeAssistant) -> bool:
    """Add the sidebar dashboard. Returns True if this call registered it."""
    try:
        from homeassistant.components import frontend
        from homeassistant.components.lovelace import dashboard
        from homeassistant.components.lovelace.const import LOVELACE_DATA

        data = hass.data.get(LOVELACE_DATA)
        if data is None:
            _LOGGER.warning("Lovelace is not loaded; dashboard not registered")
            return False
        if URL_PATH in data.dashboards:
            return False  # already registered (by the user's YAML, or a previous setup)
        conf = {
            "mode": "yaml",
            "filename": DASHBOARD_FILE,
            "title": TITLE,
            "icon": ICON,
            "show_in_sidebar": True,
            "require_admin": False,
        }
        data.dashboards[URL_PATH] = dashboard.LovelaceYAML(hass, URL_PATH, conf)
        frontend.async_register_built_in_panel(
            hass,
            "lovelace",
            frontend_url_path=URL_PATH,
            require_admin=False,
            sidebar_title=TITLE,
            sidebar_icon=ICON,
            config={"mode": "yaml"},
            update=False,
        )
        return True
    except Exception:
        _LOGGER.warning("Could not register the Smart Heating dashboard", exc_info=True)
        return False


def unregister(hass: HomeAssistant) -> None:
    """Remove the sidebar dashboard that register() added."""
    try:
        from homeassistant.components import frontend
        from homeassistant.components.lovelace.const import LOVELACE_DATA

        data = hass.data.get(LOVELACE_DATA)
        if data is not None and data.dashboards.pop(URL_PATH, None) is not None:
            frontend.async_remove_panel(hass, URL_PATH)
    except Exception:
        _LOGGER.debug("Could not unregister the Smart Heating dashboard", exc_info=True)
