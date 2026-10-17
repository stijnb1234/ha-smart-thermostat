# 06: Away and Vacation mode

**What to build:** When all tracked persons are away rooms drop to setback; long absence or Vacation mode holds frost-hold; returning resumes the schedule.

**Blocked by:** 03

**Status:** resolved

- [x] Away drops all Rooms to setback
- [x] Vacation mode for N days holds frost-hold and ends before arrival
- [x] Return home resumes schedule

Parent spec: `.scratch/smart-heating/spec.md`

## Answer

Engine: new `engine/presence.py` (`presence_setpoint`, `vacation_end`) hooked into `decide`. New inputs: `EngineInput.away_since`, `EngineInput.vacation_until`; new config `EngineConfig.prolonged_absence` (default 48 h). All away -> setback; away >= prolonged_absence -> frost-hold; Vacation (until = start of arrival day) -> frost-hold, and after it passes the schedule/pre-heat applies even if nobody is home yet (glue clears `vacation_until` once someone is home). Return home resumes schedule. Thin glue: `presence_adapter.py` (person entities) and `vacation.py` (number + switch), not yet wired into a coordinator/platform setup. Tests: `tests/engine/test_presence.py`.
