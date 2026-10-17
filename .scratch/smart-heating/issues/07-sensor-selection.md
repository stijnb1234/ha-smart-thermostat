# 07: Sensor selection

**What to build:** Rooms with an external sensor use it as truth; others use the TRV sensor with a calibration offset. External temperature is pushed to the TRV.

**Blocked by:** 00, 02

**Status:** resolved

- [x] External sensor preferred when configured
- [x] TRV sensor plus offset used otherwise
- [x] External temperature pushed to the TRV, tolerating slow delivery

Parent spec: `.scratch/smart-heating/spec.md`

## Answer

`decide()` now picks each Room temperature: external reading if younger than `SensorConfig.external_stale_after` (60 min), else TRV reading + `RoomConfig.trv_offset`, else none (`Decision.room_temps`). It also outputs `Decision.external_temp_pushes` for rooms on an external sensor: push on first reading, change >= `push_threshold` (0.3) or `push_max_interval` (15 min) since last push, tracked via `Commands.external_temp_pushed(_at)`. Inputs: `EngineInput.external_temps` / `trv_temps` (`SensorReading`). `TrvAdapter.async_push_external_temperature` publishes `{"external_temperature": x}` to `zigbee2mqtt/<name>/set` over MQTT. Tests: `tests/engine/test_sensors.py`.
