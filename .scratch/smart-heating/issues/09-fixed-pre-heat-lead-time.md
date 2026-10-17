# 09: Fixed pre-heat lead time

**What to build:** Rooms start heating before schedule so they reach comfort on time, using a configurable fixed lead time per Room.

**Blocked by:** 02

**Status:** resolved

- [x] Lead time configurable per Room
- [x] Room starts heating lead-time early on schedule transitions

Parent spec: `.scratch/smart-heating/spec.md`

## Answer

Branch `ticket-09`. `RoomConfig.lead_time` (default 70 min = 60 + 10 burner latency, `DEFAULT_LEAD_TIME` in `models.py`). `_wants_comfort` in `engine/engine.py` gives comfort when a window is active now or starts within the lead time; window end is not extended. Lead time is resolved through `lead_time_for(room, learned)`, which prefers a `timedelta` in `EngineInput.learned[room.name]` over the fixed value, so ticket 10 only needs to populate `learned`. Tests: `tests/engine/test_preheat.py`.
