# Smart Heating design

Vocabulary: `GLOSSARY.md`. Decisions: `docs/adr/`. Background research: `docs/research/`.

## Goal

Lower gas use by heating only Rooms with heat demand, while keeping them comfortable at the
times they are used. About one degree of miss is accepted when the savings are meaningful.

## Shape

One custom integration (ADR-0001), configured entirely in the UI. A pure decision engine with no
Home Assistant imports sits in the middle; thin glue around it reads states and writes commands.

```
HA states ──> coordinator ──> Snapshot ──> Controller ──> engine.decide() ──> Decision
                                              │                                  │
                         learned data, trackers, presence/vacation        adapters write it
                         (stores, keyed by Room id)                       (TRVs, boiler, alerts)
```

| Part | Module(s) | Role |
|---|---|---|
| Engine | `engine/` | Target per Room by precedence (Boost > window pause > Vacation > Away > schedule with pre-heat > setback), boiler call with debounce/backoff/manual hold, TRV lost-write and hand-change detection, alerts. Pure, tested with a fake clock. |
| Controller | `controller.py` | State that lives between cycles: temperature history, unmet tracking, away start, lead times, radiator cooldown, learning (warm-ups, coast, window noise, sensor offset, habits). Pure. |
| Presence | `arrival.py`, `presence_adapter.py` | Home, away, heading home from GPS (ADR-0007). |
| Vacation | `vacation_plan.py`, `vacation.py` | Manual and calendar periods with an exact return (ADR-0007). |
| Hardware | `boiler_adapter.py`, `trv_adapter.py`, `trv_devices.py` | Boiler call and TRVs behind adapters; TRV extras discovered on the device (ADR-0006). |
| Config | `config_flow.py`, `rooms.py`, `settings.py`, `migration.py` | Options flow, Room validation and stable ids, config entry migrations. |
| Insight | `explain.py`, `status.py`, `dashboard.py`, `report*.py`, `diagnostics.py` | Plain-language sentences, generated dashboard (ADR-0005), weekly report, diagnostics. |

## Defaults

Comfort 19.5 °C, setback 16 °C, frost-hold 12 °C. Schedule presets: living area daily
06:00–23:00, working room Mon/Wed/Fri 08:00–17:00, bedroom working hours plus a pre-bed warm-up.
Timing defaults (debounce, backoff, settle times, lead time) are in
`docs/research/phase0-findings.md`; all are configurable.

## Open items

- TRVs that take no external temperature: compensate their setpoint for the difference between
  their own sensor and the room sensor.
- More boiler adapters (relay switch, OpenTherm).
- Floor-loop actuators: floor heating only calls the boiler today.
