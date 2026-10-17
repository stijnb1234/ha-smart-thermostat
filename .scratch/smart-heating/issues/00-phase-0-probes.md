# 00: Phase 0 probes

**What to build:** Measure the undocumented behaviour of the real devices and record the results, so control logic is built on facts (ADR-0004). Results are written to a findings note and set the defaults for debounce time, pre-heat and fallback behaviour.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] EasyControl: latency from setpoint write to burner start, measured over several writes
- [ ] EasyControl: whether a raised setpoint persists or reverts, and for how long
- [ ] EasyControl: Bosch cloud rate limit found by controlled bursts, including the 429 response shape
- [ ] TRV: how long external-temperature pushes take to arrive, and what the TRV does after pushes stop
- [ ] TRV: report timing of local temperature, setpoint and valve position through Zigbee2MQTT
- [ ] Findings note written, with recommended debounce time, default pre-heat lead time and fallback behaviour

Parent spec: `.scratch/smart-heating/spec.md`
