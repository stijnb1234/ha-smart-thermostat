# 08: Alerts and Bosch outage fallback

**What to build:** Alerts for a TRV offline, low battery, or a Room that never reaches its target, plus a safe fallback when the Bosch cloud fails.

**Blocked by:** 03, 07

**Status:** resolved

- [x] Each alert fires on its condition and clears when resolved
- [x] Bosch outage leaves Rooms in a safe state and alerts
- [x] No duplicate alert spam

Parent spec: `.scratch/smart-heating/spec.md`

## Answer

Alerts are level-based in `engine/alerts.py` (`compute_alerts`, returned in `Decision.alerts`): `trv_offline` (no TRV report for 60 min), `low_battery`, `target_not_reached` (below target longer than `AlertConfig.target_window`, default 3 h; `track_unmet` maintains the since-timestamps), and `bosch_outage` (3 consecutive failed EasyControl writes). Thresholds live in `AlertConfig`. During an outage TRVs keep their last setpoints and EasyControl writes stay throttled by the existing backoff, which doubles as the recovery probe. `AlertNotifier` dedupes the active set into raised/cleared events; `alerts_adapter.py` maps them to persistent notifications (create once, dismiss on clear). New `EngineInput` fields: `trv_last_seen`, `battery_low`, `unmet_since`. Tests: `tests/engine/test_alerts.py`.
