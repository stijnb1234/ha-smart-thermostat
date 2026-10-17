"""Thin EasyControl adapter over the ha-bosch-pointt climate entity.

Writes only when the engine's setpoint differs from the last successful write and
reports the outcome as a WriteResult so the engine can apply backoff (ADR-0002).
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from .engine import Commands, WriteResult

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_RETRY_AFTER = re.compile(r"retry[- ]after\D{0,3}(\d+)", re.IGNORECASE)


def classify_error(exc: Exception) -> WriteResult:
    """Any error mentioning 429 or a rate limit counts as rate limited (phase0 assumption)."""
    text = str(exc)
    limited = "429" in text or "rate limit" in text.lower() or "too many requests" in text.lower()
    match = _RETRY_AFTER.search(text)
    return WriteResult(
        at=datetime.now(timezone.utc),
        status="rate_limited" if limited else "error",
        retry_after=timedelta(seconds=int(match.group(1))) if match else None,
    )


class EasyControlAdapter:
    def __init__(self, hass: HomeAssistant, entity_id: str) -> None:
        self._hass = hass
        self._entity_id = entity_id
        self._setpoint: float | None = None
        self._changed_at: datetime | None = None
        self._last_write: WriteResult | None = None

    @property
    def commands(self) -> Commands:
        return Commands(
            easycontrol_setpoint=self._setpoint,
            easycontrol_changed_at=self._changed_at,
        )

    @property
    def last_write(self) -> WriteResult | None:
        return self._last_write

    @property
    def observed_setpoint(self) -> float | None:
        """Setpoint the entity currently reports, or None when unknown."""
        state = self._hass.states.get(self._entity_id)
        if state is None:
            return None
        value = state.attributes.get("temperature")
        try:
            return None if value is None else float(value)
        except (TypeError, ValueError):
            return None

    async def async_apply(self, setpoint: float | None, reassert: bool = False) -> None:
        """Write `setpoint` if it changed (or `reassert`); None means a write is blocked."""
        if setpoint is None or (setpoint == self._setpoint and not reassert):
            return
        now = datetime.now(timezone.utc)
        try:
            await self._hass.services.async_call(
                "climate",
                "set_temperature",
                {"entity_id": self._entity_id, "temperature": setpoint},
                blocking=True,
            )
        except Exception as exc:  # noqa: BLE001 - cloud errors are not typed
            failed = classify_error(exc)
            previous = self._last_write.consecutive_failures if self._last_write else 0
            self._last_write = WriteResult(
                at=now,
                status=failed.status,
                retry_after=failed.retry_after,
                consecutive_failures=previous + 1,
            )
            return
        self._setpoint = setpoint
        self._changed_at = now
        self._last_write = WriteResult(at=now, status="ok")
