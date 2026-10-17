# 08: Alerts and Bosch outage fallback

**What to build:** Alerts for a TRV offline, low battery, or a Room that never reaches its target, plus a safe fallback when the Bosch cloud fails.

**Blocked by:** 03, 07

**Status:** resolved

- [x] Each alert fires on its condition and clears when resolved
- [x] Bosch outage leaves Rooms in a safe state and alerts
- [x] No duplicate alert spam

Parent spec: `.scratch/smart-heating/spec.md`

## Answer

Alerts are level-based in `engine/alerts.py` (`compute_alerts`, returned in `Decision.alerts`): `trv_offline` (no TRV report for 60 min), `low_battery`, `target_not_reached` (below target longer than `AlertConfig.target_window`, default 3 h; `track_unmet` maintains the since-timestamps), and `bosch_outage` (3 consecutive failed EasyControl writes). Thresholds live in `AlertConfig`. During an outage EasyControl writes stay throttled by the backoff, which doubles as the recovery probe, and the alert is raised. TRVs are NOT frozen (review fix): TRV control goes through Zigbee2MQTT, independent of the Bosch cloud, and freezing them would cancel Boost, window pause and schedule setback (a room could stay comfortable all night). The original freeze (`{**trv_setpoints, **last_commands.trv_setpoints}`) was removed; no test needed it. Also added: `sensor_stale` alert (external sensor silent > 2 h) and the report now includes alert history. `AlertNotifier` dedupes the active set into raised/cleared events; `alerts_adapter.py` maps them to persistent notifications (create once, dismiss on clear). New `EngineInput` fields: `trv_last_seen`, `battery_low`, `unmet_since`. Tests: `tests/engine/test_alerts.py`.
