Status: ready-for-agent

# Smart room-by-room heating

Covers design phases 1-3. Phase 0 probes (ADR-0004) and floor heating are separate. Vocabulary from `GLOSSARY.md`; decisions in `docs/adr/0001`-`0004`; facts in `docs/research/ha-heating-integrations.md`.

## Problem Statement

The home is heated by one boiler that fires whenever the Bosch EasyControl in living room right calls for heat, and every radiator takes the heat. The household pays for gas to warm rooms nobody uses (working room on non-work days, bedroom during the day, everything when away). Smart TRVs exist in five rooms but nothing coordinates them with the boiler call, the people's routine, or each room's warm-up time.

## Solution

A custom Home Assistant integration that gives each Room a target temperature from schedule, presence, boost and vacation mode, drives the Smart TRVs and the EasyControl setpoint accordingly, learns how long each room needs to pre-heat, pauses a room when a window seems open, and reports gas savings and problems. Everything is configured from the Home Assistant UI and a dashboard.

## User Stories

1. As a resident, I want the living area (living left, living right, sunroom) at comfort temperature from 06:00 to 23:00, so that it is warm when we are up.
2. As a resident, I want rooms to drop to setback outside their schedule, so that we do not heat empty rooms.
3. As a resident, I want setback to default to 16 degC and comfort to 19.5 degC, so that the house saves gas without damp risk.
4. As a resident, I want to change comfort, setback and frost-hold per Room in the UI, so that I can tune without editing files.
5. As a home worker, I want the working room heated Mon/Wed/Fri 08:00-17:00, so that it is warm only when I work there.
6. As a home worker, I want to change the work days and hours easily, so that a changed routine needs no code change.
7. As a parent, I want the bedroom heated during my son's work hours, so that he can work comfortably.
8. As a resident, I want a short bedroom warm-up before bed, so that going to bed is not cold.
9. As a resident, I want the bedroom otherwise at setback at night, so that we do not heat while sleeping.
10. As a resident, I want all Rooms to drop to setback when every tracked person is away, so that an empty house costs little.
11. As a resident, I want the house to return to schedule when someone comes home, so that I do not have to touch anything.
12. As a resident, I want a long absence to drop rooms to frost-hold (12 degC), so that the house is protected but cheap.
13. As a traveller, I want to start Vacation mode for N days, so that rooms hold frost-hold and return to normal before I arrive.
14. As a resident, I want a Boost button for any room, so that I can heat it now for a set time.
15. As a resident, I want Boost to end by itself, so that I never leave a room heating by mistake.
16. As a resident, I want a Manual-room override button for rooms with only dumb TRVs, so that the boiler fires when I turn on such a radiator.
17. As a resident, I want Manual-room override to expire after a set time and return the EasyControl to normal, so that the boiler stops later.
18. As a resident, I want the boiler to fire only when at least one Room has unmet heat demand, so that gas is not burned for nothing.
19. As a resident, I want the EasyControl setpoint changed rarely and with debounce, so that the Bosch cloud rate limit is respected.
20. As a resident, I want the system to handle a Bosch cloud failure safely, so that rooms fall back to a safe state and I get an alert.
21. As a resident, I want rooms to be warm at schedule time, so that pre-heat starts early enough.
22. As a resident, I want pre-heat lead time learned per Room from past warm-ups and outdoor temperature, so that it adapts to the 1930 house.
23. As a resident, I want a fixed configurable lead time until enough warm-ups are learned, so that early use still works.
24. As a resident, I want learned values to survive restarts, so that learning is not lost.
25. As a resident, I want a Room to stop heating when its temperature drops fast (open window), so that gas does not escape through windows.
26. As a resident, I want open-window sensitivity tunable per Room and disableable, so that false positives from doors can be handled.
27. As a resident, I want a paused Room to resume after 15-30 minutes, so that it recovers without intervention.
28. As a resident, I want rooms with external sensors (living right, kitchen, bedroom) to use them as truth, so that readings are not skewed by hot radiators.
29. As a resident, I want other rooms to use the TRV sensor with a calibration offset, so that accuracy is acceptable without extra hardware.
30. As a resident, I want external temperatures pushed to the TRV, so that its valve follows the real room temperature.
31. As a resident, I want the system to accept slow Zigbee delivery of external temperature, so that control does not oscillate.
32. As a resident, I want ensuite doors ignored, so that zones stay simple and predictable.
33. As a resident, I want alerts when a TRV is offline, battery is low, or a Room never reaches its target, so that I notice problems.
34. As a resident, I want a weekly report of gas use, heated hours per Room and issues, so that I see the effect.
35. As a resident, I want gas use compared as m3 per heating-degree-day against last year, so that savings are measured fairly.
36. As a resident, I want a dashboard showing each Room's state, target, why it is heating, and next change, so that behaviour is explainable.
37. As a resident, I want the dashboard to edit schedules, Boost, Vacation mode and Manual-room override, so that daily use needs no YAML.
38. As an installer, I want a setup flow mapping each Room to its TRV, optional external sensor and schedule, so that adding a Room is simple.
39. As a maintainer, I want the control decision separated from device adapters, so that behaviour is testable without Home Assistant.

## Implementation Decisions

- One custom Home Assistant integration (ADR-0001) with config flow and options flow for Rooms, entity mapping, temperatures, schedules, persons, vacation and alert settings.
- **Decision engine** (single test seam): pure logic taking config, current time, presence, room temperatures, learned warm-up data and last issued commands, and returning desired TRV setpoints, desired EasyControl setpoint, and alerts. It owns schedule resolution, away/vacation precedence, Boost, Manual-room override, pre-heat timing, window-open pause and the debounce/rate-limit policy.
- Precedence of a Room's target: Boost > window-open pause > Vacation mode > Away > schedule (with pre-heat) > setback.
- **Boiler call**: any Room with demand yields a raised EasyControl setpoint; no demand returns it to a low setpoint. Changes are debounced and 429-safe (ADR-0002). Bypass valve exists, so all valves may be closed.
- **Adapters**: TRV adapter over Zigbee2MQTT entities (setpoint, external temperature push, calibration offset, `valve_position` where useful; ADR-0003); EasyControl adapter over the `ha-bosch-pointt` entities; presence adapter over HA person entities; gas meter adapter over a user-chosen entity.
- Window-open detection is a rate-of-fall rule over the Room temperature; Z2M exposes no such feature.
- Pre-heat learner stores per-Room warm-up rate versus outdoor temperature in HA storage with migration support, and exposes the estimated lead time.
- Outputs exposed as HA entities (climate per Room, sensors for lead time and state reason, buttons for Boost, switch/number for Vacation mode) plus a dashboard card or panel.
- Defaults: comfort 19.5 degC, setback 16 degC, frost-hold 12 degC; living area 06:00-23:00; working room Mon/Wed/Fri 08:00-17:00; bedroom follows work hours plus a pre-bed warm-up.
- Floor heating (kitchen, bathroom) and dumb-TRV rooms' direct control are not controlled by the engine; only the Manual-room override touches them via the boiler call.

## Testing Decisions

- A good test drives the decision engine through its input/output interface with a fake clock and fake inputs, and asserts observable commands and alerts, never internal state or call order.
- Tested module: the decision engine (single seam). Scenarios: schedule transitions, away and return, vacation, Boost expiry, Manual-room override expiry, pre-heat with fixed and learned lead times, window-open pause and resume, debounce and 429 backoff, sensor choice (external vs TRV with offset), Bosch outage fallback, TRV offline alert.
- Adapters are not unit-tested; their unknown behaviour is covered by Phase 0 probes (ADR-0004), and a thin smoke test may run against fakes.
- Prior art: none; the repo has no tests yet. Use pytest, with `pytest-homeassistant-custom-component` only if a second seam is added later.

## Out of Scope

- Phase 0 probes.
- Floor heating pre-heat and mixing-valve loops.
- Door-state-aware zones.
- Guest mode, voice control, calendar-based work days.
- Controlling dumb TRVs directly.
- Changing the Bosch weekly program.

## Further Notes

- Unverified facts that may force changes: EasyControl write-to-burner latency, setpoint persistence, Bosch rate limits, TRV fallback when external-temperature pushes stop.
- Gas meter entity is still unknown; savings reporting depends on it.
- Dashboard form (standard cards, custom card, custom panel) is an open decision.
