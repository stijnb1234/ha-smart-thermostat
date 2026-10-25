"""Thin TRV adapter: writes engine setpoints to any climate entity and pushes the external
room temperature where the TRV takes one (see trv_devices.py).

Writes only when the desired setpoint differs from the last one written, so a
schedule transition results in exactly one write per Room. A failing write is
logged and skipped (retried next cycle); it never blocks the other Rooms.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Collection, Mapping
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from .apply import call_service
from .trv_devices import TrvDevice

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


MODE_FIX_MIN_INTERVAL = timedelta(minutes=2)
MODE_FIX_MIN_ATTEMPTS = 3
MODE_FIX_GIVE_UP_AFTER = timedelta(minutes=10)


class TrvAdapter:
    def __init__(self, hass: HomeAssistant, devices: Mapping[str, TrvDevice]) -> None:
        """devices maps Room name to what its TRV offers."""
        self._hass = hass
        self._devices = dict(devices)
        self._entities = {room: d.climate for room, d in devices.items()}
        self._written: dict[str, float] = {}
        self._written_at: dict[str, datetime] = {}
        self._previous: dict[str, float] = {}
        self._off_since: dict[str, datetime] = {}
        self._mode_attempts: dict[str, int] = {}
        self._mode_attempt_at: dict[str, datetime] = {}

    def restore(
        self,
        written: Mapping[str, float],
        written_at: Mapping[str, datetime],
        previous: Mapping[str, float],
    ) -> None:
        """Resume what was written before a restart, so hand changes are not overwritten."""
        self._written.update(written)
        self._written_at.update(written_at)
        self._previous.update(previous)

    def stuck_off(self) -> frozenset[str]:
        """Rooms whose TRV stayed switched off despite repeated attempts to turn it on."""
        now = datetime.now(UTC)
        return frozenset(
            room
            for room, since in self._off_since.items()
            if self._mode_attempts.get(room, 0) >= MODE_FIX_MIN_ATTEMPTS
            and now - since >= MODE_FIX_GIVE_UP_AFTER
        )

    async def async_fix_modes(self) -> None:
        """Turn a TRV that is switched off back on (heat, else auto); it ignores setpoints when off."""
        now = datetime.now(UTC)
        for room, entity_id in self._entities.items():
            state = self._hass.states.get(entity_id)
            if state is None or state.state != "off":
                self._off_since.pop(room, None)
                self._mode_attempts.pop(room, None)
                self._mode_attempt_at.pop(room, None)
                continue
            self._off_since.setdefault(room, now)
            last = self._mode_attempt_at.get(room)
            if last is not None and now - last < MODE_FIX_MIN_INTERVAL:
                continue
            modes = state.attributes.get("hvac_modes") or []
            mode = next((m for m in ("heat", "auto") if m in modes), None)
            if mode is None:
                continue
            self._mode_attempts[room] = self._mode_attempts.get(room, 0) + 1
            self._mode_attempt_at[room] = now
            _LOGGER.info("TRV %s is switched off; setting mode to %s", entity_id, mode)
            try:
                await call_service(
                    self._hass, "climate", "set_hvac_mode", {"entity_id": entity_id, "hvac_mode": mode}
                )
            except Exception:
                _LOGGER.exception("Setting %s to %s failed", entity_id, mode)

    @property
    def written(self) -> Mapping[str, float]:
        return self._written

    @property
    def written_at(self) -> Mapping[str, datetime]:
        return self._written_at

    @property
    def previous(self) -> Mapping[str, float]:
        """Per Room, the setpoint the TRV reported just before our latest change of target."""
        return self._previous

    def observed(self, room: str) -> float | None:
        """Setpoint the TRV currently reports, or None when unavailable."""
        entity_id = self._entities.get(room)
        state = self._hass.states.get(entity_id) if entity_id else None
        if state is None or state.state in ("unavailable", "unknown"):
            return None
        try:
            value = state.attributes.get("temperature")
            return None if value is None else float(value)
        except (TypeError, ValueError):
            return None

    async def async_apply(
        self, setpoints: Mapping[str, float], force: Collection[str] = ()
    ) -> None:
        """Write changed setpoints, plus those in `force` even though unchanged (lost write)."""
        for room, target in setpoints.items():
            entity_id = self._entities.get(room)
            unchanged = self._written.get(room) == target
            if entity_id is None or (unchanged and room not in force):
                continue
            before = self.observed(room)
            try:
                await call_service(
                    self._hass, "climate", "set_temperature", {"entity_id": entity_id, "temperature": target}
                )
            except Exception:  # service errors are not typed; TimeoutError when it hangs
                _LOGGER.exception("Setting %s to %s failed; retrying next cycle", entity_id, target)
                continue
            if not unchanged:
                prior = before if before is not None else self._written.get(room)
                if prior is None:
                    self._previous.pop(room, None)
                else:
                    self._previous[room] = prior
            _LOGGER.info("TRV %s set to %s (was %s)", entity_id, target, before)
            self._written[room] = target
            self._written_at[room] = datetime.now(UTC)

    def takes_external_temperature(self, room: str) -> bool:
        """Whether a pushed room temperature can reach this Room's TRV at all."""
        device = self._devices.get(room)
        if device is None:
            return False
        return device.external_number is not None or (device.mqtt_topic is not None and self._mqtt_available())

    def _mqtt_available(self) -> bool:
        has_service = getattr(self._hass.services, "has_service", None)
        return has_service is None or has_service("mqtt", "publish")

    async def async_push_external_temperature(self, pushes: Mapping[str, float]) -> set[str]:
        """Give each TRV the external room temperature: through its number entity, else over
        Zigbee2MQTT (delivery to the sleepy device may take minutes, ADR-0003, so this is fire
        and forget). Returns the Rooms done; failed ones are retried next cycle. A TRV that takes
        no external temperature counts as done: there is nothing to retry.
        """
        done: set[str] = set()
        for room, value in pushes.items():
            device = self._devices.get(room)
            try:
                if device is not None and device.external_number is not None:
                    await call_service(
                        self._hass, "number", "set_value",
                        {"entity_id": device.external_number, "value": round(value, 1)},
                    )
                elif device is not None and device.mqtt_topic is not None and self._mqtt_available():
                    await call_service(
                        self._hass, "mqtt", "publish",
                        {"topic": device.mqtt_topic, "payload": json.dumps({"external_temperature": value})},
                    )
            except Exception:
                _LOGGER.exception("Pushing external temperature for %s failed", room)
                continue
            done.add(room)
        return done
