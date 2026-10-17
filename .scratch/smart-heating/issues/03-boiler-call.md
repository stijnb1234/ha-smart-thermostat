# 03: Boiler call

**What to build:** Any Room with unmet heat demand raises the EasyControl setpoint; with none it returns to the low setpoint. Changes are debounced and handle HTTP 429.

**Blocked by:** 00, 02

**Status:** resolved

- [x] No demand: EasyControl at low setpoint
- [x] Demand in one or more Rooms: raised setpoint
- [x] Rapid demand changes do not flood the cloud API
- [x] A 429 response backs off and retries

Parent spec: `.scratch/smart-heating/spec.md`

## Answer

Engine (`engine/boiler.py`) aggregates demand (any Room with a reading below its target), picks the low or high EasyControl setpoint, debounces changes (5 min since last change) and backs off after failed writes (5, 10, 20, 30 min cap, `Retry-After` honoured; any error treated alike, per phase 0 assumptions). The adapter reports each write as a `WriteResult` input. All constants are `EngineConfig` fields. Thin adapter: `easycontrol_adapter.py`. Tests: `tests/engine/test_boiler_call.py`. Not done: periodic re-assert of the setpoint (needs observed entity state).
