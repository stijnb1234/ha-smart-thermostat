# 02: Schedule-driven room targets

**What to build:** Rooms follow comfort and setback schedules: living area 06:00-23:00, working room Mon/Wed/Fri 08:00-17:00, bedroom during work hours. TRV setpoints are written over Zigbee2MQTT.

**Blocked by:** 01

**Status:** resolved

- [x] Comfort 19.5 and setback 16 are defaults per Room
- [x] Working room demand only on configured days and hours
- [x] Bedroom follows work hours
- [x] TRV adapter sets the setpoint on schedule transitions

Parent spec: `.scratch/smart-heating/spec.md`

## Answer

Branch `ticket-02`. Schedule resolution in `custom_components/smart_heating/engine/engine.py` (`ScheduleWindow` in `models.py`, spec default schedules exported); tests in `tests/engine/test_schedule.py`. TRV adapter: `custom_components/smart_heating/trv_adapter.py` (writes via `climate.set_temperature` only when the setpoint changes; not yet wired into a coordinator, boiler call is ticket 03).
