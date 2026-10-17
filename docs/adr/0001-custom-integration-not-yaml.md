# Build as a custom Home Assistant integration, not YAML helpers

The system is a custom integration with a config/options flow UI, Python control logic, persisted learning data and a dashboard. Considered YAML package + helpers (faster to start) and reusing HACS Scheduler/Versatile Thermostat; rejected because learned pre-heat, per-room options in one UI and unit-testable logic need real code, and the boiler-call logic is custom anyway.
