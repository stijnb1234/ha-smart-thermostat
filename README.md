# Smart Heating

[![Open in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=stijnb1234&repository=ha-smart-thermostat&category=integration)
[![Validate](https://github.com/stijnb1234/ha-smart-thermostat/actions/workflows/validate.yml/badge.svg)](https://github.com/stijnb1234/ha-smart-thermostat/actions/workflows/validate.yml)

Room-by-room heating for Home Assistant. One boiler, several radiators: the boiler fires only when a room actually wants heat, and rooms nobody uses stay cool.

**Living with it?** The user manual explains the Overview screen, the buttons and what each message means, without the technical details: [English](https://github.com/stijnb1234/ha-smart-thermostat/blob/main/docs/manual.en.md) · [Nederlands](https://github.com/stijnb1234/ha-smart-thermostat/blob/main/docs/manual.nl.md).

## Features

**Rooms and the boiler**

- Each **Room** gets a target temperature from its schedule, presence, Boost and Vacation mode (comfort 19.5 °C, setback 16 °C, frost-hold 12 °C by default).
- Drives **any smart TRV** that Home Assistant shows as a `climate` entity (Zigbee2MQTT, ZHA, cloud valves): setpoint, calibration offset, and a valve that is switched off is turned back on. What the valve offers beyond that is found on its device: a battery sensor, valve opening, heating demand, and an **external room temperature** input (a number entity in °C, or Zigbee2MQTT over MQTT), so the valve regulates on the room's own thermometer. A valve that cannot take one gets its setpoint corrected instead: target plus the difference between its sensor and the room sensor (rounded, capped, with a deadband so it is not rewritten all the time; can be switched off per room).
- Fires the boiler by raising the setpoint of the **boiler thermostat** (any `climate` entity that makes the boiler fire) only while at least one room has unmet demand; debounced, rate-limit safe, and a hung cloud call times out after 30 s instead of stalling the rest.
- **Pre-heat** so rooms are warm at schedule time. The lead time follows how far the room has to come right now (a room back from frost-hold starts earlier, a room that is still warm later): learned per room from past warm-ups and the outdoor temperature, the fixed lead time scaled by the shortfall until then. Once pre-heat starts it is not cut short.
- **Open-radiator** rooms (no TRV yet, temperature sensor required) call the boiler while cold, and once such a room reaches its comfort temperature all boiler calls stop until it has cooled 0.3 °C (no flapping), so other rooms cannot heat the house past it. Use this for rooms whose smart valves are not installed yet; switch the flag off after installing them.
- **Floor heating** rooms (no TRV, temperature sensor required) follow their schedule with a long pre-heat (3 h by default, then learned), call the boiler while cold, and keep idle radiators at frost-hold during that pre-heat so the flow goes to the floor loops. Assumes the loops are always open.

**Presence**

- **Away**: everyone out drops rooms to setback; after 48 h, to frost-hold. The 48 h count from the moment the house became empty and survive restarts and zone changes.
- **Heading home, automatically**: from the GPS position the Home Assistant app reports, Smart Heating sees someone coming closer at travel speed and estimates when they arrive. Within the time the house needs to warm up, Away ends and their rooms warm up. No zones to draw. Extra signals (a switch you flip, a zone) can be added.
- **Vacation**: pick when you are back and switch Vacation mode on, use the `smart_heating.set_vacation` service, or let a calendar do it (events with "vacation", "holiday" or "vakantie" in the title, keywords configurable). The house holds frost-hold; each room starts warming up just in time for your return.
- **Per-room occupants**: link a room to people or entities (person, device tracker, binary sensor, switch). While all of them are away, the room skips its schedule and pre-heat and stays at setback. Boost still wins. Unknown or unavailable entities count as present; someone heading home counts as present.

**Automatic behaviour**

- **Open-window detection**: a fast temperature drop (read from the TRV sensor, which sits nearest the window) pauses a room for 15–30 min. While a radiator cools down after heating, the TRV sensor falls although the room does not; for that hour only the external room sensor counts. The configured drop is a ceiling: each room learns its own normal fluctuation and uses a lower, tighter threshold once it has about 3 hours of quiet data.
- **Self-learning** (persisted, per room, with safe fallbacks until there is data):
  - *Coast*: how far a room keeps rising after the boiler call ends (upper quartile of recent observations); the call then ends that much earlier to avoid overshoot. While the room is still warming from the radiator's stored heat it does not call again, unless it is clearly cold.
  - *Sensor offset*: the difference between the external sensor and the TRV sensor while the radiator is idle, used when only the TRV reading is available (unless an offset is set by hand).
  - *Not warming*: a room that calls for heat for 45 min without warming 0.3 °C raises an alert (open window or a radiator that does not work).
  - *Schedule suggestions*: Boosts and hand-set valves on at least 3 different days around the same time outside the schedule show up in the Monday report as a suggested schedule window. Nothing changes by itself.
- **Hand changes are respected** (and survive restarts):
  - A temperature set on a radiator valve stays until that room's target next changes. It calls the boiler if it is above the room's setback and the room is colder than that.
  - A TRV that never took the temperature we sent gets it again, up to 3 times, then raises an alert.
  - A change on the boiler thermostat is respected for 2 hours (configurable under advanced settings). If what you set is what Smart Heating wants anyway when that ends, it is simply adopted.

**Controls and insight**

- **Boost** buttons per room (or the `smart_heating.boost` service with your own duration), and a **Manual-room override** that calls the boiler for rooms with ordinary radiator valves.
- **Alerts**: TRV offline or switched off, TRV not accepting its setpoint, low battery, a comfort room clearly below target for hours, boiler thermostat unreachable, stale sensor. Shown under the bell, and optionally pushed to notify services (your phone) once an alert has lasted a set time (15 min by default), with a message when it is resolved.
- **Rename freely**: each room has a stable id, so renaming it keeps its entities, history and everything it learned.
- **Weekly gas report** every Monday: m³ per heating-degree-day vs last year, hours each room called the boiler, open issues.
- A generated **dashboard** with a plain-language overview, a page per room, a boiler page and a help page.
- **English and Dutch**, following Home Assistant's language (Settings > System > General): options screens, entity names, dashboard sentences, alerts and the weekly report. Reload the integration after changing the language. Schedule text accepts Dutch day names (ma, di, wo, do, vr, za, zo, dagelijks).

Not controlled: the floor loops themselves (floor heating only calls the boiler), dumb TRVs (except through the Manual-room override), door-aware zones.

## Requirements

- Home Assistant 2025.1 or newer.
- Smart TRVs as `climate.*` entities. For the external room temperature: a number entity on the valve's device (°C), or Zigbee2MQTT with the MQTT integration (base topic configurable).
- A boiler thermostat as a `climate.*` entity. Optional: without it, no boiler call is made.
- `person.*` entities for presence (optional); the Home Assistant app with location for automatic heading-home detection.
- A calendar entity for automatic vacations (optional).
- A gas meter entity and an outdoor temperature sensor with long-term statistics, for the weekly report (optional).

## Installation

Via HACS (custom repository), or click the badge above:

1. HACS → ⋮ → **Custom repositories**.
2. Repository: `https://github.com/stijnb1234/ha-smart-thermostat`, category **Integration** → **Add**.
3. Find **Smart Heating** in HACS → **Download**.
4. Restart Home Assistant.
5. Settings → Devices & services → **Add integration** → **Smart Heating**.

Manually: copy `custom_components/smart_heating` into your config's `custom_components/` and restart.

## Configuration

Everything is configured in the UI: Settings → Devices & services → Smart Heating → **Configure**. Changes apply without restarting Home Assistant.

| Menu | What you set |
|---|---|
| Add / edit / remove a room | Name, TRV entity, optional external sensor, comfort / setback / frost-hold, schedule preset (living area, working room, bedroom, none) or custom schedule text, offset, lead time, window detection, occupants and their heading-home signal. Rooms flagged *manual* have no TRV and only act through the Manual-room override; *floor heating* rooms have no TRV and need a sensor. |
| Boiler, presence and vacation | Boiler thermostat, tracked persons, automatic heading-home detection (on by default) and extra heading-home signals, vacation calendar and keywords (`*` = every event), low / high boiler thermostat setpoints, Boost and override durations, bedroom pre-bed window. |
| Boiler call and alert thresholds | Debounce, backoff, demand hysteresis, alert thresholds, battery %, notify services for alerts and their delay, Zigbee2MQTT base topic. |
| Gas report settings | Gas meter entity, outdoor sensor, heating-degree-day base (default 18 °C). |

Schedule text: one comfort window per line, e.g.

```
daily 06:00-23:00
mon,wed,fri 08:00-17:00
mon-fri 07:00-09:00
```

Presets: living area 06:00–23:00; working room Mon/Wed/Fri 08:00–17:00; bedroom follows work hours plus a pre-bed warm-up (default 21:30–22:30).

## Dashboard

On setup the integration writes `smart_heating_dashboard.yaml` into your config folder and registers it as a **Smart Heating** dashboard in the sidebar. Nothing to configure.

| Page | Contents |
|---|---|
| Overview | Status line, a table of all rooms, alerts when there are any, all controls. The [manual](https://github.com/stijnb1234/ha-smart-thermostat/blob/main/docs/manual.en.md) covers this page for everyday users. |
| Heating | One section per room: summary, next change, lead time, Boost, a 24 h temperature graph and the valve's battery, opening and heating demand (found on the valve's device). |
| Boiler | Call status, demand rooms, last write and its result, backoff, boiler thermostat manual hold, Manual-room override. |
| Help | Short cards on how to read the dashboard. |

Schedules are edited through the integration's Configure dialog (linked from the dashboard).

The registration uses Home Assistant internals. If it ever fails (see the log), register the file by hand in `configuration.yaml`:

```yaml
lovelace:
  dashboards:
    smart-heating:
      mode: yaml
      title: Smart Heating
      icon: mdi:radiator
      show_in_sidebar: true
      filename: smart_heating_dashboard.yaml
```

## Entities

Per room (`<domain>.smart_heating_<room id>[_<key>]`; the id is set from the name when the room is added and kept on rename): a read-only `climate` (its action is *heating* only while the room actually calls the boiler), sensors for *reason* (machine value), *summary* (plain sentence, e.g. "Warm from 17:00"), *next change* and *lead time*, and Boost and cancel-boost `button`s.

System-wide: a Vacation `switch` and return `datetime`, Manual-room override start and cancel `button`s, `sensor.smart_heating_status`, `sensor.smart_heating_active_alerts` (count, plain-language `messages` attribute), `binary_sensor.smart_heating_boiler_call` and `sensor.smart_heating_boiler_*` (`demand_rooms`, `target`, `last_write`, `write_result`, `backoff`, `manual_hold`).

## Services

| Service | What it does |
|---|---|
| `smart_heating.boost` | Target one or more room climate entities; optional `duration` (default: the configured Boost). |
| `smart_heating.cancel_boost` | Stop a Boost. |
| `smart_heating.set_vacation` | `end` (when you are back), optional `start` (default now). |
| `smart_heating.cancel_vacation` | End a manual vacation (calendar vacations follow the calendar). |

Example: warm the bathroom for 20 minutes when the morning alarm goes off.

```yaml
action: smart_heating.boost
target:
  entity_id: climate.smart_heating_bathroom
data:
  duration: "00:20:00"
```

## How decisions are made

Target precedence per room: **Boost > open-window pause > Vacation > Away > schedule (with pre-heat; skipped while the room's occupants are away) > setback**. The boiler is called only for rooms whose target is comfort and whose temperature is below it by more than the hysteresis, plus hand-set valves as described above.

All decision logic lives in a pure Python engine (`custom_components/smart_heating/engine/`) with no Home Assistant imports, tested with a fake clock. See `GLOSSARY.md`, `docs/adr/` and `docs/design.md`.

## Assumptions

Cloud and Zigbee timing could not be measured, so defaults were assumed and are all configurable: debounce 5 min, max one write per 2 min, 429 backoff 5→30 min, a hand change on the boiler thermostat respected for 2 h, a TRV write checked after 10 min, default pre-heat lead time 70 min for comfort minus setback. Details and how to verify each are in `docs/research/phase0-findings.md`.

## Troubleshooting

- *Boiler never fires*: check the boiler thermostat is set under *Boiler, presence and vacation* and its integration can write setpoints; look for `boiler_outage` / rate-limit alerts.
- *Room ignores external sensor*: readings older than 60 min fall back to the TRV sensor plus offset; a sensor silent for 2 h raises an alert. Check the diagnostics (below) for whether the valve takes an external temperature at all.
- *Window pause when nothing was open*: the log line `Open window in <room>: … K drop` shows the drop and which sensor saw it.
- Otherwise, open an [issue](https://github.com/stijnb1234/ha-smart-thermostat/issues) with the diagnostics (Settings → Devices & services → Smart Heating → ⋮ → **Download diagnostics**; people and calendars are redacted, locations never included) and debug logs (`custom_components.smart_heating: debug`).

## Development

```bash
python3.13 -m venv .venv && .venv/bin/pip install -r requirements-test.txt
.venv/bin/ruff check .   # lint
.venv/bin/mypy           # types (stricter for the pure engine)
.venv/bin/pytest -q      # engine tests plus Home Assistant smoke tests
```

The engine (`engine/`) and the pure glue modules have no Home Assistant imports and run against a fake clock; `tests/ha/` loads the integration in a real test Home Assistant. CI runs all three plus hassfest and the HACS check.

Releasing: bump `version` in `manifest.json`, then push a tag `v<version>`; the release workflow checks they match and publishes the GitHub release.

## License

[MIT](LICENSE)
