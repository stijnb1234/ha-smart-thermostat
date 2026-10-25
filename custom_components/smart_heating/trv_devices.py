"""Pure discovery of what a TRV offers, from its device's entities. No HA imports.

Any climate entity works as a TRV (setpoint and hvac mode are standard). Extras are found on
the same device: a battery sensor, a number entity that takes an external room temperature
(over Zigbee2MQTT or ZHA), valve position and heating demand. A Zigbee2MQTT TRV without such a
number gets the temperature over MQTT instead. A TRV with none of this simply regulates on its
own sensor.
"""

from __future__ import annotations

import re
from collections.abc import Collection, Sequence
from dataclasses import dataclass

DEFAULT_Z2M_BASE_TOPIC = "zigbee2mqtt"

_EXTERNAL_TEMP = re.compile(r"(external|remote).*temp|external_measured_room_sensor")
_VALVE = re.compile(r"valve.*(position|opening)|position.*valve")
_DEMAND = re.compile(r"heating_demand|pi_heating")
_CELSIUS = ("°C", "C")


@dataclass(frozen=True)
class DeviceEntity:
    entity_id: str
    device_class: str | None = None
    unit: str | None = None
    name: str = ""  # original name or translation key, as extra matching text

    @property
    def domain(self) -> str:
        return self.entity_id.split(".", 1)[0]

    @property
    def text(self) -> str:
        return f"{self.entity_id.split('.', 1)[-1]} {self.name}".lower().replace(" ", "_")


@dataclass(frozen=True)
class TrvDevice:
    climate: str
    battery: str | None = None
    external_number: str | None = None  # number entity taking the room temperature (°C)
    mqtt_topic: str | None = None  # Zigbee2MQTT set topic, when there is no such number
    valve_position: str | None = None
    heating_demand: str | None = None

    @property
    def takes_external_temperature(self) -> bool:
        return self.external_number is not None or self.mqtt_topic is not None


def _first(entities: Sequence[DeviceEntity], domains: Collection[str], pattern: re.Pattern[str]) -> str | None:
    return next((e.entity_id for e in entities if e.domain in domains and pattern.search(e.text)), None)


def is_z2m(identifiers: Collection[tuple[str, str]]) -> bool:
    return any(domain == "mqtt" and str(ident).startswith("zigbee2mqtt") for domain, ident in identifiers)


def resolve_trv(
    climate: str,
    entities: Sequence[DeviceEntity],
    device_name: str | None,
    identifiers: Collection[tuple[str, str]],
    base_topic: str = DEFAULT_Z2M_BASE_TOPIC,
) -> TrvDevice:
    """What the TRV behind `climate` offers. `entities` are the other entities of its device."""
    battery = next(
        (e.entity_id for e in entities if e.domain == "sensor" and e.device_class == "battery"), None
    )
    external = next(
        (
            e.entity_id
            for e in entities
            if e.domain == "number" and e.unit in _CELSIUS and _EXTERNAL_TEMP.search(e.text)
        ),
        None,
    )
    topic = None
    if external is None and device_name and is_z2m(identifiers):
        # Zigbee2MQTT names the HA device after the friendly name it publishes under.
        topic = f"{base_topic}/{device_name}/set"
    return TrvDevice(
        climate=climate,
        battery=battery,
        external_number=external,
        mqtt_topic=topic,
        valve_position=_first(entities, ("number", "sensor"), _VALVE),
        heating_demand=_first(entities, ("sensor",), _DEMAND),
    )


def fallback_trv(climate: str, base_topic: str = DEFAULT_Z2M_BASE_TOPIC) -> TrvDevice:
    """Without a device registry entry: the Zigbee2MQTT naming convention (friendly name equals
    the entity's object id), as Smart Heating assumed before discovery existed."""
    name = climate.split(".", 1)[-1]
    return TrvDevice(
        climate=climate,
        battery=f"sensor.{name}_battery",
        mqtt_topic=f"{base_topic}/{name}/set",
        valve_position=f"number.{name}_valve_position",
        heating_demand=f"sensor.{name}_pi_heating_demand",
    )
