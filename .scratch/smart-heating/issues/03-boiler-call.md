# 03: Boiler call

**What to build:** Any Room with unmet heat demand raises the EasyControl setpoint; with none it returns to the low setpoint. Changes are debounced and handle HTTP 429.

**Blocked by:** 00, 02

**Status:** ready-for-agent

- [ ] No demand: EasyControl at low setpoint
- [ ] Demand in one or more Rooms: raised setpoint
- [ ] Rapid demand changes do not flood the cloud API
- [ ] A 429 response backs off and retries

Parent spec: `.scratch/smart-heating/spec.md`
