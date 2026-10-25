"""Thin HA glue: turns alert changes from the engine into persistent notifications."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from .const import DOMAIN
from .engine import Alert, AlertNotifier
from .status import alert_sentence

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


def _notification_id(alert: Alert) -> str:
    return f"{DOMAIN}_{alert.code}_{alert.room or 'system'}"


class AlertAdapter:
    def __init__(self, hass: HomeAssistant, lang: str = "en") -> None:
        self._hass = hass
        self._lang = lang
        self._notifier = AlertNotifier()

    @property
    def notifier(self) -> AlertNotifier:
        """Exposes `history` and `active` for the weekly report."""
        return self._notifier

    async def async_apply(self, alerts: tuple[Alert, ...]) -> None:
        changes = self._notifier.update(alerts, datetime.now(UTC))
        for alert in changes.raised:
            await self._hass.services.async_call(
                "persistent_notification",
                "create",
                {
                    "title": "Smart Heating",
                    "message": alert_sentence(alert, self._lang),
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
