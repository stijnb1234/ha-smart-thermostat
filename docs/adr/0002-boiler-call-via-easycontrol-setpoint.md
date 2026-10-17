# Boiler call-for-heat is a raised EasyControl setpoint, rate-limited

The only way to fire the boiler is the Bosch EasyControl in living room right, driven through the `ha-bosch-pointt` cloud integration (60 s polling, rotating OAuth token, undocumented rate limits). The controller therefore changes the EasyControl setpoint rarely, debounces changes and handles HTTP 429, instead of toggling per room. Smart TRVs gate which rooms receive the heat. A bypass valve exists, so all valves may be closed.

## Consequences

- Heat reaches rooms only after cloud latency plus Zigbee latency; pre-heat lead time must include both.
- Bosch cloud outage means no boiler call; TRVs must still fall back to a safe state.
