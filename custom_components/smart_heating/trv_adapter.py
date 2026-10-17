"""Thin TRV adapter: writes engine setpoints to Zigbee2MQTT climate entities.

Writes only when the desired setpoint differs from the last one written, so a
schedule transition results in exactly one write per Room. A failing write is
logged and skipped (retried next cycle); it never blocks the other Rooms.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Collection, Mapping

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


MODE_FIX_MIN_INTERVAL = timedelta(minutes=2)
MODE_FIX_MIN_ATTEMPTS = 3
MODE_FIX_GIVE_UP_AFTER = timedelta(minutes=10)


class TrvAdapter:
    def __init__(self, hass: HomeAssistant, entities: Mapping[str, str]) -> None:
        """entities maps Room name to the Z2M climate entity id."""
        self._hass = hass
        self._entities = dict(entities)
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
        now = datetime.now(timezone.utc)
        return frozenset(
            room
            for room, since in self._off_since.items()
            if self._mode_attempts.get(room, 0) >= MODE_FIX_MIN_ATTEMPTS
            and now - since >= MODE_FIX_GIVE_UP_AFTER
        )

    async def async_fix_modes(self) -> None:
        """Turn a TRV that is switched off back on (heat, else auto); it ignores setpoints when off."""
        now = datetime.now(timezone.utc)
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
                await self._hass.services.async_call(
                    "climate",
                    "set_hvac_mode",
                    {"entity_id": entity_id, "hvac_mode": mode},
                    blocking=True,
                )
            except Exception:  # noqa: BLE001
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
                await self._hass.services.async_call(
                    "climate",
                    "set_temperature",
                    {"entity_id": entity_id, "temperature": target},
                    blocking=True,
                )
            except Exception:  # noqa: BLE001 - service errors are not typed
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
            self._written_at[room] = datetime.now(timezone.utc)

    async def async_push_external_temperature(
        self, pushes: Mapping[str, float], z2m_names: Mapping[str, str]
    ) -> set[str]:
        """Publish external room temperature to zigbee2mqtt/<name>/set.

        z2m_names maps Room name to the Z2M friendly name. Delivery to the
        sleepy device may take minutes (ADR-0003), so this is fire and forget.
        Returns the Rooms whose push succeeded (failed ones are retried next cycle).
        """
        pushed: set[str] = set()
        for room, value in pushes.items():
            name = z2m_names.get(room)
            if name is None:
                continue
            try:
                await self._hass.services.async_call(
                    "mqtt",
                    "publish",
                    {
                        "topic": f"zigbee2mqtt/{name}/set",
                        "payload": json.dumps({"external_temperature": value}),
                    },
                    blocking=True,
                )
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Pushing external temperature for %s failed", room)
                continue
            pushed.add(room)
        return pushed
