# Smart heating design

Status: draft from the grilling session. Facts and sources: `docs/research/ha-heating-integrations.md`. Vocabulary: `GLOSSARY.md`. Decisions: `docs/adr/`.

## Goal

Lower gas use by heating only rooms with heat demand. Comfort at scheduled times is balanced against savings (about 1 degree of miss accepted if savings are meaningful).

## Rooms and defaults (all configurable in UI)

| Room | Smart TRV | Demand source |
|---|---|---|
| Living left, living right, sunroom | yes | Living-area schedule 06:00-23:00 |
| Working room | yes | Mon/Wed/Fri 08:00-17:00 (editable) |
| Bedroom | yes | Son's work hours, plus short pre-bed warm-up |
| Kitchen, bathroom | no (floor heating) | Later phase |
| Other rooms | dumb TRVs | Manual boost button only |

- Comfort 19.5 degC everywhere, setback 16 degC, frost-hold 12 degC.
- Away (all HA persons not home): all rooms to setback; long absence or vacation mode to frost-hold.
- External sensors: living right, kitchen, bedroom. Others use TRV sensor plus offset.
- Ensuite doors ignored; fixed zones.

## Architecture

One custom integration (`ADR-0001`):

1. **Config/options flow**: rooms, entity mapping (TRV, external sensor), temperatures, schedules, presence persons.
2. **Room model**: per room target (comfort/setback/frost-hold) from schedule, presence, boost, vacation.
3. **Demand aggregator**: any room with unmet demand yields a boiler call; otherwise EasyControl returns to a low setpoint (`ADR-0002`).
4. **TRV driver**: sets TRV setpoint over Z2M MQTT entities and pushes external temperature (`ADR-0003`).
5. **Pre-heat learner**: per-room warm-up rate vs outdoor temperature, persisted with HA `Store`. Fixed lead time until enough data.
6. **Window detector**: rate-of-fall rule, per-room sensitivity, pauses room for 15-30 min.
7. **Reporting**: weekly report, alerts (TRV offline, low battery, target not reached), gas m3 per heating-degree-day against last year (needs gas meter entity).
8. **Dashboard**: card or panel for schedules, boost buttons, vacation mode, guest toggle not required.

## Phases

0. **Probes** (`ADR-0004`): EasyControl write latency and persistence, 429 behaviour, TRV external-temperature fallback, Z2M report timing.
1. **Core**: rooms, schedules, setback, demand aggregator, boiler call, boost.
2. **Presence, vacation mode, alerts, weekly report.**
3. **Learned pre-heat, window detection.**
4. **Floor heating**: long pre-heat with other TRVs closed, via mixing-valve loops (controller details unknown).

## Open items

- Phase 0 results.
- Dashboard form (standard cards vs custom card vs panel).
- Floor-loop actuator type.
- Gas meter entity for savings measurement.
