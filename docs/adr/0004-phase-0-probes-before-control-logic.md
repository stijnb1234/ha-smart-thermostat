# Measure unknown device behaviour in a probe phase before writing control logic

EasyControl write-to-burner latency, setpoint persistence, Bosch rate limits and TRV fallback when external temperature stops are undocumented. Phase 0 measures them on the real system and the results set debounce times and pre-heat defaults; no control logic is built on assumptions.
