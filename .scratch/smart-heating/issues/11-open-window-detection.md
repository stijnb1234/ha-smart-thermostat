# 11: Open-window detection

**What to build:** A sharp temperature drop pauses a Room for 15-30 minutes, with per-Room sensitivity and an off switch.

**Blocked by:** 07

**Status:** resolved

- [x] Fast drop pauses Room heating
- [x] Room resumes after the pause
- [x] Sensitivity tunable and disableable per Room

Parent spec: `.scratch/smart-heating/spec.md`

## Answer

Implemented in `engine/window.py`, wired into `decide()`. A Room pauses when its temperature (from `EngineInput.temp_history`) falls by at least `RoomConfig.window_drop` (default 1.5 degC) within `window_period` (10 min). While paused the TRV target is `frost_hold`. The pause lasts `window_pause` (default 20 min, clamped to 15-30), then the Room resumes. State is carried via `Decision.window_paused_until`, fed back as `Commands.window_paused_until`. Per-Room `window_drop` (sensitivity) and `window_detection` (enabled flag). Boost is not wired yet; the pause is applied after schedule resolution, so Boost must override it when added. Tests: `tests/engine/test_window.py`.
