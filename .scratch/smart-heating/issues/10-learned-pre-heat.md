# 10: Learned pre-heat

**What to build:** Lead time is learned per Room from warm-up rate versus outdoor temperature and persisted across restarts.

**Blocked by:** 09

**Status:** resolved

- [x] Lead time adapts after observed warm-ups
- [x] Fixed lead time used until enough data exists
- [x] Learned data survives a restart

Parent spec: `.scratch/smart-heating/spec.md`

## Answer

Pure `LeadTimeLearner` in `engine/learner.py`: records warm-ups per Room (rate K/h vs outdoor temp), needs `MIN_SAMPLES` (5) before it estimates, fits rate = a + b*outdoor over the last 50 samples, lead = delta / rate clamped to 10 min - 4 h. `lead_times(outdoor, deltas)` returns the `{room: timedelta}` mapping for `EngineInput.learned`; rooms without enough data are omitted so the engine falls back to the fixed `RoomConfig.lead_time`. State serialises via `to_dict`/`from_dict` with `version` (current 2; v1 migrated; unknown versions give an empty learner). `learner_store.py` wraps the HA `Store`. Wiring into the coordinator (recording warm-ups, feeding `learned`) is left to integration. Tests: `tests/engine/test_learner.py`.
