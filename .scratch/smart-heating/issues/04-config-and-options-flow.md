# 04: Config and options flow

**What to build:** Rooms, TRV and optional external sensor mapping, temperatures and schedules are editable from the HA UI.

**Blocked by:** 02

**Status:** resolved

- [x] Add, edit and remove a Room in the UI
- [x] Schedules and temperatures editable per Room
- [x] Changes take effect without restarting HA

Parent spec: `.scratch/smart-heating/spec.md`

## Answer

Branch `ticket-04`. Pure mapping/validation in `custom_components/smart_heating/rooms.py` (stored room dicts <-> engine `RoomConfig`, add/replace/remove with name and TRV uniqueness, temperature ordering, text schedule parser); tests in `tests/config/test_rooms.py`. Engine models untouched: TRV and sensor entities live in the stored room and are exposed via `trv_entities()` / `sensor_entities()`. Rooms are stored in config entry options (`rooms`). `config_flow.py` has a menu-based options flow (add/edit/remove/save); `__init__.py` registers an update listener that reloads the entry, so changes apply without restart. HA flow glue is not exercised by tests (HA not installed in the venv).
