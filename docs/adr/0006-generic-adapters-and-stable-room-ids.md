# Generic boiler and TRV adapters, stable Room ids

Smart Heating was built around one home: a Bosch EasyControl as the boiler call (ADR-0002) and
Shelly BLU TRVs on Zigbee2MQTT whose friendly name equals the entity object id (ADR-0003). To work
in other homes the hardware sits behind adapters:

- **Boiler**: a `BoilerAdapter` protocol. The only implementation, `ThermostatBoilerAdapter`, raises
  the setpoint of any climate entity that drives the boiler (EasyControl included). Option keys and
  engine names say `boiler_*` instead of `easycontrol_*`.
- **TRVs**: any climate entity. Battery, external-temperature input, valve position and heating
  demand are discovered from the entities on the TRV's device (`trv_devices.py`). The external
  temperature goes to a number entity in °C when the device has one (Zigbee2MQTT and ZHA alike),
  else over MQTT to `<base topic>/<device name>/set` for Zigbee2MQTT devices. Without a device the
  old naming convention is the fallback.

Rooms get a stable id, set once from the name and kept on rename. Entity unique ids, entity ids,
the generated dashboard and all stored data (learned lead times, insights, bookkeeping, Boosts) are
keyed by it; the engine keeps using names, translated at the storage boundary (`RoomKeys`).

Config entry version 2 migrates option keys, assigns ids and moves entity unique ids.

## Consequences

- A rename keeps history, entity ids and learned data.
- A TRV that takes no external temperature gets a corrected setpoint instead (target plus its
  sensor's difference with the room sensor, rounded, capped at 5 K, with a deadband); the Room's
  target, demand and hand-change detection stay in Room terms.
- Other boiler calls (relay, OpenTherm) are a new adapter, not engine changes.
