# 05: Boost and Manual-room override

**What to build:** A Boost button heats a Room now for a set time. A Manual-room override fires the boiler for dumb-TRV rooms. Both expire on their own.

**Blocked by:** 03

**Status:** resolved

- [x] Boost raises a Room to comfort and expires
- [x] Manual-room override raises the boiler call and expires
- [x] After expiry the system returns to normal behaviour

Parent spec: `.scratch/smart-heating/spec.md`

## Answer

Added `engine/overrides.py` with `Boost` and `ManualRoomOverride` (start + duration, active in [start, start+duration)). `EngineInput` gains `boosts` (per Room) and `manual_overrides`. `decide` sets a boosted Room to comfort (top precedence, beats Away) and treats any active Manual-room override as boiler demand; both lapse on their own once the duration passes, restoring normal behaviour. HA glue in `button.py`: a Boost button per Room and one Manual-room override button, storing the request in the entry state for the coordinator to pass to the engine. Tests: `tests/engine/test_overrides.py` (fake clock).
