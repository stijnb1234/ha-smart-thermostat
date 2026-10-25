from datetime import timedelta

from homeassistant.config_entries import ConfigEntryState
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from custom_components.smart_heating.const import DOMAIN

from .conftest import ROOMS, set_home, setup_entry


async def test_config_flow_creates_a_single_entry(hass):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] == "create_entry"
    assert result["result"].version == 2
    again = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    assert again["type"] == "abort" and again["reason"] == "already_configured"


async def test_setup_creates_entities_and_calls_for_heat(hass, service_calls):
    set_home(hass, bed_temp=17.0)  # comfort 19.5 all day: the room calls for heat
    entry = await setup_entry(hass)
    assert entry.state is ConfigEntryState.LOADED

    climate = hass.states.get("climate.smart_heating_bed")
    assert climate is not None and climate.attributes["temperature"] == 19.5
    assert hass.states.get("binary_sensor.smart_heating_boiler_call").state == "on"
    assert hass.states.get("switch.smart_heating_vacation_mode").state == "off"
    assert hass.states.get("datetime.smart_heating_vacation_return") is not None
    assert ("climate", "set_temperature", {"entity_id": "climate.boiler", "temperature": 22.0}) in service_calls
    # No MQTT and no external-temperature number: the valve regulates on its own sensor, which
    # reads 18 against 17 in the room, so it gets the 19.5 target corrected by +1.
    assert ("climate", "set_temperature", {"entity_id": "climate.bed_trv", "temperature": 20.5}) in service_calls
    assert climate.attributes["hvac_action"] == "heating"


async def test_boost_service_with_duration(hass):
    set_home(hass, bed_temp=21.0)
    await setup_entry(hass)
    await hass.services.async_call(
        DOMAIN, "boost", {"entity_id": "climate.smart_heating_bed", "duration": {"minutes": 15}}, blocking=True
    )
    await hass.async_block_till_done()
    boost = hass.data[DOMAIN]["e1"]["boosts"]["Bedroom"]
    assert boost.duration == timedelta(minutes=15)
    assert hass.states.get("sensor.smart_heating_bed_reason").state == "boost"

    await hass.services.async_call(DOMAIN, "cancel_boost", {"entity_id": "climate.smart_heating_bed"}, blocking=True)
    assert "Bedroom" not in hass.data[DOMAIN]["e1"]["boosts"]


async def test_vacation_service_and_switch(hass):
    set_home(hass, person="not_home")
    await setup_entry(hass)
    back = dt_util.now() + timedelta(days=5)
    await hass.services.async_call(DOMAIN, "set_vacation", {"end": back}, blocking=True)
    await hass.async_block_till_done()
    switch = hass.states.get("switch.smart_heating_vacation_mode")
    assert switch.state == "on" and switch.attributes["until"] is not None
    await hass.data[DOMAIN]["e1"]["coordinator"].async_refresh()
    assert hass.states.get("sensor.smart_heating_bed_reason").state == "vacation"

    await hass.services.async_call("switch", "turn_off", {"entity_id": "switch.smart_heating_vacation_mode"}, blocking=True)
    assert hass.states.get("switch.smart_heating_vacation_mode").state == "off"


async def test_migration_from_version_1_moves_options_and_unique_ids(hass):
    set_home(hass)
    v1_rooms = [{k: v for k, v in r.items() if k != "id"} for r in ROOMS]
    registry = er.async_get(hass)
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    entry = MockConfigEntry(
        domain=DOMAIN, version=1, entry_id="e1",
        options={"rooms": v1_rooms, "easycontrol_entity": "climate.boiler", "easycontrol_high": 23},
    )
    entry.add_to_hass(hass)
    registry.async_get_or_create(
        "climate", DOMAIN, "e1_climate_Bedroom", config_entry=entry, suggested_object_id="smart_heating_bedroom"
    )
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.version == 2
    assert entry.options["boiler_entity"] == "climate.boiler" and entry.options["boiler_high"] == 23
    assert entry.options["rooms"][0]["id"] == "bedroom"
    migrated = registry.async_get("climate.smart_heating_bedroom")
    assert migrated.unique_id == "e1_climate_bedroom"


async def test_trv_extras_are_found_on_its_device(hass):
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    z2m = MockConfigEntry(domain="mqtt")
    z2m.add_to_hass(hass)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=z2m.entry_id, identifiers={("mqtt", "zigbee2mqtt_0xabc")}, name="Bedroom TRV"
    )
    registry = er.async_get(hass)
    registry.async_get_or_create("climate", "mqtt", "0xabc_climate", device_id=device.id, suggested_object_id="bed_trv")
    registry.async_get_or_create(
        "sensor", "mqtt", "0xabc_battery", device_id=device.id, original_device_class="battery", suggested_object_id="bed_trv_power"
    )
    set_home(hass)
    await setup_entry(hass)

    trv = hass.data[DOMAIN]["e1"]["coordinator"].trv_devices["Bedroom"]
    assert trv.battery == "sensor.bed_trv_power"
    assert trv.mqtt_topic == "zigbee2mqtt/Bedroom TRV/set"


async def test_unload_flushes_learned_data_and_diagnostics_work(hass):
    from custom_components.smart_heating.diagnostics import async_get_config_entry_diagnostics

    set_home(hass)
    entry = await setup_entry(hass)
    diag = await async_get_config_entry_diagnostics(hass, entry)
    assert diag["version"] == 2 and diag["options"]["persons"] == "**REDACTED**"
    assert diag["last_cycle"]["reasons"] == {"Bedroom": "schedule"}

    coordinator = hass.data[DOMAIN]["e1"]["coordinator"]
    coordinator.controller.insights.record_coast("Bedroom", 0.3)
    coordinator.controller.insights_dirty = True
    assert await hass.config_entries.async_unload(entry.entry_id)
    stored = coordinator._p.insights_store._store  # the flush wrote it under the Room id
    data = await stored.async_load()
    assert data["coasts"] == {"bed": [0.3]}


async def test_alerts_are_pushed_to_configured_notify_services(hass):
    from pytest_homeassistant_custom_component.common import async_mock_service

    from .conftest import OPTIONS

    sent = async_mock_service(hass, "notify", "phone")
    set_home(hass)
    hass.states.async_set("sensor.bed_trv_battery", "8")  # low battery alert
    await setup_entry(hass, {**OPTIONS, "notify_targets": ["notify.phone"], "notify_delay_minutes": 0})
    assert [c.data["message"] for c in sent] == ["The battery of the radiator valve in Bedroom is low. Replace it soon."]

    hass.states.async_set("sensor.bed_trv_battery", "90")
    await hass.data[DOMAIN]["e1"]["coordinator"].async_refresh()
    assert sent[-1].data["message"].startswith("Resolved: ")


async def test_options_flow_saves_notify_and_correction_settings(hass):
    set_home(hass)
    entry = await setup_entry(hass)
    flow = await hass.config_entries.options.async_init(entry.entry_id)
    flow = await hass.config_entries.options.async_configure(flow["flow_id"], {"next_step_id": "advanced_settings"})
    assert flow["step_id"] == "advanced_settings"
    flow = await hass.config_entries.options.async_configure(
        flow["flow_id"], {"notify_targets": ["notify.phone"], "notify_delay_minutes": 30}
    )
    flow = await hass.config_entries.options.async_configure(flow["flow_id"], {"next_step_id": "save"})
    assert flow["type"] == "create_entry"
    assert entry.options["notify_targets"] == ["notify.phone"] and entry.options["notify_delay_minutes"] == 30
