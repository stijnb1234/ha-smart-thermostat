# Phase 0 findings: assumed defaults (not measured)

Status: **assumptions**. Probes (ADR-0004) were not run; long-term tests are not possible. Every value below is a configurable default, to be verified in production. `scripts/phase0/` can still be run later to replace these with measurements.

## Assumptions

| Area | Assumption | Default | Verify in prod by |
|---|---|---|---|
| EasyControl write -> burner start | Cloud poll (60 s) + Bosch/boiler delay; several minutes | 10 min added to pre-heat lead time | Log time from setpoint write to `hvac_action: heating` |
| Setpoint persistence | Write goes to `clockOverride/temperatureHeating`; may revert at next weekly-program switch | If the observed setpoint differs from ours 10 min after our write, treat it as a manual change: make no EasyControl writes for 2 h (hold), then write the desired setpoint if it still differs; never assume it persists. (Replaces the earlier 30-min re-assert, which would have undone hand changes almost at once.) Settle and hold length are configurable | Log reverts (state differs from last written without our write) |
| Rate limit | Unknown; Bosch cloud is strict | Debounce 5 min after demand change, max 1 write per 2 min, 429 -> exponential backoff 5 -> 10 -> 20 -> 30 min, honour `Retry-After` | Count 429s in alert log; tune debounce |
| 429 response shape | Surfaces as an HA service error / log line mentioning 429 | Adapter treats any write error mentioning 429 or rate limit as 429; other errors retry with same backoff | Capture first real 429 text, then match precisely |
| TRV external-temperature delivery | Sleepy Zigbee device; delivery within minutes, retried up to 1 h (ADR-0003) | Push on change >= 0.3 degC and at least every 15 min; control tolerates 1 h staleness | Compare pushed vs TRV-reported external temp |
| TRV fallback when pushes stop | TRV reverts to internal sensor, possibly after a timeout | Treat room reading as TRV sensor + offset when external reading older than 60 min; alert if stale > 2 h | Stop pushes once, observe |
| TRV report timing | Local temperature/setpoint/valve reports within ~1-10 min | Treat TRV state older than 30 min as stale -> TRV offline alert after 60 min | Log `last_updated` gaps |
| Default pre-heat lead time | 1930 house, slow radiators | 60 min before schedule, plus the burner latency above | Learner (ticket 10) replaces it |
| Boiler fallback on Bosch outage | No boiler call possible | TRVs keep following the schedule (Zigbee, independent of the cloud); EasyControl writes throttled by the backoff; alert after 3 failed writes | Observe an outage |

## Consequences for tickets

- 03 Boiler call: debounce/backoff constants above, all configurable.
- 07 Sensor selection: stale-reading thresholds above.
- 08 Alerts: offline/stale/outage thresholds above.
- 09/10 Pre-heat: default lead time 60 min + 10 min.
