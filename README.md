# Smart Heating

[![Open in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=stijnb1234&repository=ha-smart-thermostat&category=integration)
[![Validate](https://github.com/stijnb1234/ha-smart-thermostat/actions/workflows/validate.yml/badge.svg)](https://github.com/stijnb1234/ha-smart-thermostat/actions/workflows/validate.yml)

Room-by-room heating for Home Assistant. One boiler, several radiators: the boiler fires only when a room actually wants heat, and rooms nobody uses stay cool.

**Living with it?** The user manual explains the Overview screen, the buttons and what each message means, without the technical details: [English](https://github.com/stijnb1234/ha-smart-thermostat/blob/main/docs/manual.en.md) · [Nederlands](https://github.com/stijnb1234/ha-smart-thermostat/blob/main/docs/manual.nl.md).

## Features

**Rooms and the boiler**

- Each **Room** gets a target temperature from its schedule, presence, Boost and Vacation mode (comfort 19.5 °C, setback 16 °C, frost-hold 12 °C by default).
- Drives **Zigbee2MQTT smart TRVs**: setpoint, external room temperature, calibration offset. A valve that is switched off is turned back on.
- Fires the boiler by raising the **Bosch EasyControl** setpoint (via [`ha-bosch-pointt`](https://github.com/stijnb1234/ha-bosch-pointt)) only while at least one room has unmet demand; debounced and 429-safe.
- **Pre-heat** so rooms are warm at schedule time: a fixed lead time at first, then a lead time learned per room from past warm-ups and the outdoor temperature.
- **Floor heating** rooms (no TRV, temperature sensor required) follow their schedule with a long pre-heat (3 h by default, then learned), call the boiler while cold, and keep idle radiators at frost-hold during that pre-heat so the flow goes to the floor loops. Assumes the loops are always open.

**Presence**

- **Away**: everyone out drops rooms to setback; after 48 h, to frost-hold.
- **Vacation mode** holds frost-hold for a set number of days and is back on schedule from midnight on the day you return.
- **Per-room occupants**: link a room to people or entities (person, device tracker, binary sensor, switch). While all of them are away, the room skips its schedule and pre-heat and stays at setback. Boost still wins. Unknown or unavailable entities count as present.
- **Heading home**: an optional signal (a person entering a "near home" zone, a switch you flip) cancels a room's occupant skip within its schedule. The same signal exists globally and ends Away or Vacation early, so the house is warm when you arrive.

**Automatic behaviour**

- **Open-window detection**: a fast temperature drop pauses a room for 15–30 min.
- **Hand changes are respected** (and survive restarts):
  - A temperature set on a radiator valve stays until that room's target next changes. It calls the boiler if it is above the room's setback and the room is colder than that.
  - A TRV that never took the temperature we sent gets it again, up to 3 times, then raises an alert.
  - A change on the EasyControl is respected for 2 hours (configurable under advanced settings).

**Controls and insight**

- **Boost** buttons per room, and a **Manual-room override** that calls the boiler for rooms with ordinary radiator valves.
- **Alerts**: TRV offline or switched off, TRV not accepting its setpoint, low battery, room never reaches target, Bosch outage, stale sensor.
- **Weekly gas report** every Monday: m³ per heating-degree-day vs last year, heated hours per room, open issues.
- A generated **dashboard** with a plain-language overview, a page per room, a boiler page and a help page.
- **English and Dutch**, following Home Assistant's language (Settings > System > General): options screens, entity names, dashboard sentences, alerts and the weekly report. Reload the integration after changing the language. Schedule text accepts Dutch day names (ma, di, wo, do, vr, za, zo, dagelijks).

Not controlled: the floor loops themselves (floor heating only calls the boiler), dumb TRVs (except through the Manual-room override), door-aware zones.

## Requirements

- Home Assistant 2025.1 or newer.
- MQTT integration with Zigbee2MQTT, TRVs exposed as `climate.*` entities (the Z2M friendly name is assumed to equal the climate entity's object id; battery sensor assumed `sensor.<name>_battery`).
- Bosch EasyControl via `ha-bosch-pointt` (a `climate.*` entity). Optional: without it, no boiler call is made.
- `person.*` entities for presence (optional).
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
| Boiler and presence settings | EasyControl entity, tracked persons, heading-home signal, low / high EasyControl setpoints, Boost and override durations, bedroom pre-bed window. |
| Boiler call and alert thresholds | Debounce, backoff, demand hysteresis, alert thresholds, battery %. |
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
| Heating | One section per room: summary, next change, lead time, Boost, a 24 h temperature graph and the valve's battery, opening and heating demand (assumed `sensor.<name>_battery`, `number.<name>_valve_position`, `sensor.<name>_pi_heating_demand`). |
| Boiler | Call status, demand rooms, last write and its result, backoff, EasyControl manual hold, Manual-room override. |
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

Per room (`<domain>.smart_heating_<room>[_<key>]`): a read-only `climate`, sensors for *reason* (machine value), *summary* (plain sentence, e.g. "Warm from 17:00"), *next change* and *lead time*, and Boost and cancel-boost `button`s.

System-wide: a Vacation `switch` and days `number`, Manual-room override start and cancel `button`s, `sensor.smart_heating_status`, `sensor.smart_heating_active_alerts` (count, plain-language `messages` attribute), `binary_sensor.smart_heating_boiler_call` and `sensor.smart_heating_boiler_*` (`demand_rooms`, `target`, `last_write`, `write_result`, `backoff`, `manual_hold`).

## How decisions are made

Target precedence per room: **Boost > open-window pause > Vacation > Away > schedule (with pre-heat; skipped while the room's occupants are away) > setback**. The boiler is called only for rooms whose target is comfort and whose temperature is below it by more than the hysteresis, plus hand-set valves as described above.

All decision logic lives in a pure Python engine (`custom_components/smart_heating/engine/`) with no Home Assistant imports, tested with a fake clock. See `GLOSSARY.md`, `docs/adr/` and `docs/design.md`.

## Assumptions

The Bosch cloud and Zigbee timing could not be measured, so defaults were assumed and are all configurable: debounce 5 min, max one write per 2 min, 429 backoff 5→30 min, a hand change on the EasyControl respected for 2 h, a TRV write checked after 10 min, default pre-heat lead time 70 min. Details and how to verify each are in `docs/research/phase0-findings.md`.

## Troubleshooting

- *Boiler never fires*: check the EasyControl entity is set under *Boiler and presence settings* and the Bosch integration can write setpoints; look for `bosch_outage` / rate-limit alerts.
- *Room ignores external sensor*: readings older than 60 min fall back to the TRV sensor plus offset; a sensor silent for 2 h raises an alert.
- Otherwise, open an [issue](https://github.com/stijnb1234/ha-smart-thermostat/issues) with debug logs (`custom_components.smart_heating: debug`).

## Development

```bash
python -m venv .venv && .venv/bin/pip install -r requirements-test.txt
.venv/bin/pytest -q
```

## License

[MIT](LICENSE)
