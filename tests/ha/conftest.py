"""Home Assistant smoke tests: the integration loaded in a real (test) Home Assistant."""

from unittest.mock import patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.smart_heating.const import DOMAIN

ROOMS = [
    {
        "id": "bed",
        "name": "Bedroom",
        "trv_entity": "climate.bed_trv",
        "sensor_entity": "sensor.bed_temp",
        "schedule": [{"days": [0, 1, 2, 3, 4, 5, 6], "start": "00:00", "end": "23:59"}],
    },
]
OPTIONS = {"rooms": ROOMS, "boiler_entity": "climate.boiler", "persons": ["person.alex"]}


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture(autouse=True)
def no_dashboard_file():
    with patch("custom_components.smart_heating._write_dashboard"):
        yield


@pytest.fixture
def service_calls(hass):
    """Every service call made, as (domain, service, data)."""
    calls = []
    hass.bus.async_listen("call_service", lambda e: calls.append((e.data["domain"], e.data["service"], e.data["service_data"])))
    return calls


def set_home(hass, *, bed_temp=17.0, person="home"):
    hass.states.async_set("climate.bed_trv", "heat", {"temperature": 16.0, "current_temperature": 18.0, "hvac_modes": ["off", "heat"]})
    hass.states.async_set("sensor.bed_temp", str(bed_temp), {"unit_of_measurement": "°C"})
    hass.states.async_set("climate.boiler", "heat", {"temperature": 15.0})
    hass.states.async_set("person.alex", person, {})


async def setup_entry(hass, options=None, version=2):
    entry = MockConfigEntry(domain=DOMAIN, version=version, options=options or OPTIONS, entry_id="e1")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry
