# 01: Skeleton and first behaviour

**What to build:** The integration loads in Home Assistant and the decision engine, driven by a fake clock and fake inputs, puts a configured Room at setback. Test setup is in place.

**Blocked by:** None (can start immediately)

**Status:** resolved

- [x] Integration installs and loads in HA without errors
- [x] Engine returns the setback target for a Room with no demand
- [x] Engine tests run with a fake clock and no HA dependency

Parent spec: `.scratch/smart-heating/spec.md`

## Answer

Branch `ticket-01`. Engine: `custom_components/smart_heating/engine/` (`decide(EngineInput) -> Decision`, pure Python). Tests: `tests/engine/test_setback.py` with `FakeClock` in `tests/conftest.py`; run `pytest`. HA skeleton (manifest, `__init__.py`, config flow stub) is in `custom_components/smart_heating/`; not yet load-tested inside a real HA instance (HA not installed in the dev venv).
