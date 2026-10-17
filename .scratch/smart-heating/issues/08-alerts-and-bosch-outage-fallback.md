# 08: Alerts and Bosch outage fallback

**What to build:** Alerts for a TRV offline, low battery, or a Room that never reaches its target, plus a safe fallback when the Bosch cloud fails.

**Blocked by:** 03, 07

**Status:** ready-for-agent

- [ ] Each alert fires on its condition and clears when resolved
- [ ] Bosch outage leaves Rooms in a safe state and alerts
- [ ] No duplicate alert spam

Parent spec: `.scratch/smart-heating/spec.md`
