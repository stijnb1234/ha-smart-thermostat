"""Thin TRV adapter: writes engine setpoints to Zigbee2MQTT climate entities.

Writes only when the desired setpoint differs from the last one written, so a
schedule transition results in exactly one write per Room.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Mapping

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


class TrvAdapter:
    def __init__(self, hass: HomeAssistant, entities: Mapping[str, str]) -> None:
        """entities maps Room name to the Z2M climate entity id."""
        self._hass = hass
        self._entities = dict(entities)
        self._written: dict[str, float] = {}

    @property
    def written(self) -> Mapping[str, float]:
        return self._written

    async def async_apply(self, setpoints: Mapping[str, float]) -> None:
        for room, target in setpoints.items():
            entity_id = self._entities.get(room)
            if entity_id is None or self._written.get(room) == target:
                continue
            await self._hass.services.async_call(
                "climate",
                "set_temperature",
                {"entity_id": entity_id, "temperature": target},
                blocking=True,
            )
            self._written[room] = target

    async def async_push_external_temperature(
        self, pushes: Mapping[str, float], z2m_names: Mapping[str, str]
    ) -> None:
        """Publish external room temperature to zigbee2mqtt/<name>/set.

        z2m_names maps Room name to the Z2M friendly name. Delivery to the
        sleepy device may take minutes (ADR-0003), so this is fire and forget.
        """
        for room, value in pushes.items():
            name = z2m_names.get(room)
            if name is None:
                continue
            await self._hass.services.async_call(
                "mqtt",
                "publish",
                {
                    "topic": f"zigbee2mqtt/{name}/set",
                    "payload": json.dumps({"external_temperature": value}),
                },
                blocking=True,
            )
