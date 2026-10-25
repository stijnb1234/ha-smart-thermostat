from custom_components.smart_heating.trv_devices import DeviceEntity, fallback_trv, resolve_trv

Z2M = {("mqtt", "zigbee2mqtt_0x1234")}
ZHA = {("zha", "00:11:22:33")}


def test_z2m_trv_without_external_number_gets_the_mqtt_topic_of_its_friendly_name():
    entities = [
        DeviceEntity("sensor.bedroom_trv_battery", device_class="battery", unit="%"),
        DeviceEntity("number.bedroom_trv_valve_position", unit="%"),
        DeviceEntity("sensor.bedroom_trv_pi_heating_demand", unit="%"),
    ]
    trv = resolve_trv("climate.bedroom_trv", entities, "Bedroom TRV", Z2M)
    assert trv.battery == "sensor.bedroom_trv_battery"
    assert trv.mqtt_topic == "zigbee2mqtt/Bedroom TRV/set" and trv.external_number is None
    assert trv.valve_position == "number.bedroom_trv_valve_position"
    assert trv.heating_demand == "sensor.bedroom_trv_pi_heating_demand"


def test_an_external_temperature_number_is_preferred_and_works_for_zha_too():
    entities = [DeviceEntity("number.living_trv_external_temperature_input", unit="°C")]
    trv = resolve_trv("climate.living_trv", entities, "Living TRV", ZHA)
    assert trv.external_number == "number.living_trv_external_temperature_input"
    assert trv.mqtt_topic is None and trv.takes_external_temperature


def test_external_number_in_other_units_is_not_used():
    # Danfoss can expose the room sensor in hundredths of a degree: pushing degrees would be wrong.
    entities = [DeviceEntity("number.x_external_measured_room_sensor", unit=None)]
    assert resolve_trv("climate.x", entities, "X", ZHA).external_number is None


def test_names_count_for_matching_not_only_entity_ids():
    entities = [DeviceEntity("number.0x1234_setting_7", unit="°C", name="Remote temperature")]
    assert resolve_trv("climate.x", entities, "X", ZHA).external_number == "number.0x1234_setting_7"


def test_plain_trv_regulates_on_its_own_sensor():
    trv = resolve_trv("climate.tado_bedroom", [], "Bedroom", {("tado", "abc")})
    assert not trv.takes_external_temperature and trv.battery is None


def test_fallback_uses_the_z2m_naming_convention():
    trv = fallback_trv("climate.0xabc", base_topic="z2m")
    assert trv.mqtt_topic == "z2m/0xabc/set" and trv.battery == "sensor.0xabc_battery"
