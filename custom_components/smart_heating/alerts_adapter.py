"""Thin HA glue: turns alert changes from the engine into persistent notifications."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .const import DOMAIN
from .engine import Alert, AlertNotifier

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


def _notification_id(alert: Alert) -> str:
    return f"{DOMAIN}_{alert.code}_{alert.room or 'system'}"


class AlertAdapter:
    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass
        self._notifier = AlertNotifier()

    async def async_apply(self, alerts: tuple[Alert, ...]) -> None:
        changes = self._notifier.update(alerts)
        for alert in changes.raised:
            await self._hass.services.async_call(
                "persistent_notification",
                "create",
                {
                    "title": "Smart Heating",
                    "message": alert.message or alert.code,
                    "notification_id": _notification_id(alert),
                },
                blocking=True,
            )
        for alert in changes.cleared:
            await self._hass.services.async_call(
                "persistent_notification",
                "dismiss",
                {"notification_id": _notification_id(alert)},
                blocking=True,
            )
