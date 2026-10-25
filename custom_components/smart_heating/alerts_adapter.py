"""Thin HA glue: turns alert changes from the engine into persistent notifications, and, when
configured, pushes them to notify services (phones) once they have lasted a while."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from .apply import call_service
from .const import DOMAIN
from .engine import Alert, AlertNotifier
from .engine.alerts import AlertPush
from .i18n import tr
from .status import alert_sentence

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


def _notification_id(alert: Alert) -> str:
    return f"{DOMAIN}_{alert.code}_{alert.room or 'system'}"


def notify_service(target: str) -> str:
    """`notify.mobile_app_phone` or `mobile_app_phone` -> `mobile_app_phone`."""
    return target.strip().removeprefix("notify.")


class AlertAdapter:
    def __init__(
        self,
        hass: HomeAssistant,
        lang: str = "en",
        notify_targets: Sequence[str] = (),
        notify_delay: timedelta = timedelta(minutes=15),
    ) -> None:
        self._hass = hass
        self._lang = lang
        self._notifier = AlertNotifier()
        self._targets = tuple(t for t in (notify_service(t) for t in notify_targets) if t)
        self._push = AlertPush(notify_delay)

    @property
    def notifier(self) -> AlertNotifier:
        """Exposes `history` and `active` for the weekly report."""
        return self._notifier

    async def async_apply(self, alerts: tuple[Alert, ...]) -> None:
        now = datetime.now(UTC)
        changes = self._notifier.update(alerts, now)
        for alert in changes.raised:
            await self._call(
                "persistent_notification",
                "create",
                {
                    "title": "Smart Heating",
                    "message": alert_sentence(alert, self._lang),
                    "notification_id": _notification_id(alert),
                },
            )
        for alert in changes.cleared:
            await self._call("persistent_notification", "dismiss", {"notification_id": _notification_id(alert)})
        if self._targets:
            await self._push_changes(alerts, now)

    async def _call(self, domain: str, service: str, data: dict) -> None:
        """One notification; a failing one must not keep the others from going out."""
        try:
            await call_service(self._hass, domain, service, data)
        except Exception:
            _LOGGER.warning("Sending a notification with %s.%s failed", domain, service, exc_info=True)

    async def _push_changes(self, alerts: tuple[Alert, ...], now: datetime) -> None:
        pushed = self._push.update(alerts, now)
        messages = [alert_sentence(a, self._lang) for a in pushed.raised]
        messages += [tr(self._lang, "alert.resolved", text=alert_sentence(a, self._lang)) for a in pushed.cleared]
        for message in messages:
            for target in self._targets:
                await self._call("notify", target, {"title": "Smart Heating", "message": message})
