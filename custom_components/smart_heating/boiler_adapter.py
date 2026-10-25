"""Boiler call adapters: how the engine's "call for heat" reaches the boiler.

The engine decides a setpoint: `boiler_high` while a Room calls for heat, `boiler_low`
otherwise (ADR-0002). An adapter turns that into a write and reports the outcome as a
WriteResult, so the engine can debounce, back off and notice manual changes.

Today there is one kind, `ThermostatBoilerAdapter`: a room thermostat that drives the boiler
(any climate entity whose setpoint makes the boiler fire). Other kinds
(a relay switch, OpenTherm) implement the same `BoilerAdapter` protocol.
"""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any, Protocol

from .apply import call_service
from .engine import Commands, WriteResult

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)
_RETRY_AFTER = re.compile(r"retry[- ]after\D{0,3}(\d+)", re.IGNORECASE)


class BoilerAdapter(Protocol):
    @property
    def commands(self) -> Commands:
        """What was last written successfully (boiler_setpoint, boiler_changed_at)."""

    @property
    def last_write(self) -> WriteResult | None: ...

    @property
    def observed_setpoint(self) -> float | None:
        """What the device reports now, for noticing manual changes (None when unknown)."""

    def restore(self, setpoint: float | None, changed_at: datetime | None) -> None: ...

    async def async_apply(self, setpoint: float | None, reassert: bool = False) -> None: ...


def classify_error(exc: BaseException) -> WriteResult:
    """Any error mentioning 429 or a rate limit counts as rate limited (phase0 assumption)."""
    text = str(exc)
    limited = "429" in text or "rate limit" in text.lower() or "too many requests" in text.lower()
    match = _RETRY_AFTER.search(text)
    return WriteResult(
        at=datetime.now(UTC),
        status="rate_limited" if limited else "error",
        retry_after=timedelta(seconds=int(match.group(1))) if match else None,
    )


class ThermostatBoilerAdapter:
    """Calls for heat by raising the setpoint of the thermostat that drives the boiler."""

    def __init__(self, hass: HomeAssistant, entity_id: str) -> None:
        self._hass = hass
        self._entity_id = entity_id
        self._setpoint: float | None = None
        self._changed_at: datetime | None = None
        self._last_write: WriteResult | None = None

    def restore(self, setpoint: float | None, changed_at: datetime | None) -> None:
        """Resume the last setpoint we set before a restart, so a hand change is still noticed."""
        self._setpoint, self._changed_at = setpoint, changed_at

    @property
    def commands(self) -> Commands:
        return Commands(boiler_setpoint=self._setpoint, boiler_changed_at=self._changed_at)

    @property
    def last_write(self) -> WriteResult | None:
        return self._last_write

    @property
    def observed_setpoint(self) -> float | None:
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
        now = datetime.now(UTC)
        try:
            await call_service(
                self._hass, "climate", "set_temperature", {"entity_id": self._entity_id, "temperature": setpoint}
            )
        except Exception as exc:  # cloud errors are not typed; TimeoutError when it hangs
            failed = classify_error(exc) if not isinstance(exc, TimeoutError) else WriteResult(now, "error")
            _LOGGER.warning(
                "Setting boiler thermostat %s to %s failed (%s): %s",
                self._entity_id, setpoint, failed.status, exc or "timed out",
            )
            previous = self._last_write.consecutive_failures if self._last_write else 0
            self._last_write = WriteResult(
                at=now,
                status=failed.status,
                retry_after=failed.retry_after,
                consecutive_failures=previous + 1,
            )
            return
        _LOGGER.info("Boiler thermostat %s set to %s (was %s)", self._entity_id, setpoint, self._setpoint)
        self._setpoint = setpoint
        self._changed_at = now
        self._last_write = WriteResult(at=now, status="ok")


def make_boiler_adapter(hass: HomeAssistant, options: dict[str, Any]) -> BoilerAdapter | None:
    """The adapter for the configured boiler call, or None when none is configured."""
    from .const import CONF_BOILER_ENTITY

    entity = options.get(CONF_BOILER_ENTITY)
    return ThermostatBoilerAdapter(hass, entity) if entity else None
