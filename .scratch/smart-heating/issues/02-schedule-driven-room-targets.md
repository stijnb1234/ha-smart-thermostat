# 02: Schedule-driven room targets

**What to build:** Rooms follow comfort and setback schedules: living area 06:00-23:00, working room Mon/Wed/Fri 08:00-17:00, bedroom during work hours. TRV setpoints are written over Zigbee2MQTT.

**Blocked by:** 01

**Status:** ready-for-agent

- [ ] Comfort 19.5 and setback 16 are defaults per Room
- [ ] Working room demand only on configured days and hours
- [ ] Bedroom follows work hours
- [ ] TRV adapter sets the setpoint on schedule transitions

Parent spec: `.scratch/smart-heating/spec.md`
