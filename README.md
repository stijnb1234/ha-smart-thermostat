# Smart Heating

[![Open in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=stijnb1234&repository=ha-smart-thermostat&category=integration)
[![Validate](https://github.com/stijnb1234/ha-smart-thermostat/actions/workflows/validate.yml/badge.svg)](https://github.com/stijnb1234/ha-smart-thermostat/actions/workflows/validate.yml)

Room-by-room heating for Home Assistant. One boiler, several radiators: the boiler fires only when a room actually wants heat, and rooms nobody uses stay cool.

> **Status: 0.1.0, untested on real hardware.** The decision engine is covered by unit tests; the Home Assistant glue has not yet run against a live system. Several timing values are assumptions to verify (see [Assumptions](#assumptions)).

## What it does

- Gives each **Room** a target temperature from schedule, presence, Boost and Vacation mode (comfort 19.5 °C, setback 16 °C, frost-hold 12 °C by default).
- Drives **Zigbee2MQTT smart TRVs** (setpoint, external room temperature, calibration offset).
- Fires the boiler by raising the **Bosch EasyControl** setpoint (via [`ha-bosch-pointt`](https://github.com/stijnb1234/ha-bosch-pointt)) only while at least one room has unmet demand; debounced and 429-safe.
- **Pre-heats** so rooms are warm at schedule time: a fixed lead time, replaced by a lead time learned per room from past warm-ups and outdoor temperature.
- **Open-window detection**: a fast temperature drop pauses a room for 15–30 min.
- **Per-room occupants**: link a room to people/entities (person, device tracker, binary sensor, switch). While all of them are away, the room skips its schedule (and pre-heat) and stays at setback. Boost still wins. Unknown or unavailable entities count as present. An optional heading-home signal (e.g. a person entering a "near home" zone, or a switch you flip) cancels the skip, so the room warms up before you arrive; it only applies within the room's schedule. The same signal exists globally (heating settings): it ends Away/Vacation early so the whole house warms before you arrive.
- **Away / Vacation**: everyone away drops rooms to setback; long absence or Vacation mode holds frost-hold and returns before you arrive.
- **Boost** buttons per room and a **Manual-room override** for rooms with dumb radiator valves.
- **Alerts** (TRV offline, low battery, room never reaches target, Bosch outage, stale sensor) and a **weekly gas report** (m³ per heating-degree-day vs last year).
- A generated **dashboard** with a plain-language overview (who is heating, boiler status, alerts), a page per room and a help page.

Not controlled: floor heating, dumb TRVs (except through the Manual-room override), door-aware zones. See `.scratch/smart-heating/spec.md`.

## Requirements

- Home Assistant 2025.1 or newer.
- MQTT integration with Zigbee2MQTT, TRVs exposed as `climate.*` entities (the Z2M friendly name is assumed to equal the climate entity's object id; battery sensor assumed `sensor.<name>_battery`).
- Bosch EasyControl via `ha-bosch-pointt` (a `climate.*` entity). Optional: without it, no boiler call is made.
- `person.*` entities for presence (optional).
- A gas meter entity and an outdoor temperature sensor with long-term statistics, for the weekly report (optional).

## Installation (HACS custom repository)

1. HACS → ⋮ → **Custom repositories**.
2. Repository: `https://github.com/stijnb1234/ha-smart-thermostat`, category **Integration** → **Add**.
3. Find **Smart Heating** in HACS → **Download**.
4. Restart Home Assistant.
5. Settings → Devices & services → **Add integration** → **Smart Heating**.

Or click the badge above.

Manual: copy `custom_components/smart_heating` into your config's `custom_components/` and restart.

## Configuration

Everything is configured in the UI: Settings → Devices & services → Smart Heating → **Configure**.

| Menu | What you set |
|---|---|
| Add / edit / remove a room | Name, TRV entity, optional external sensor, comfort / setback / frost-hold, schedule preset (living area, working room, bedroom, none) or custom schedule text, offset, lead time, window detection. Rooms flagged *manual* have no TRV and only act through the Manual-room override. |
| Boiler and presence settings | EasyControl entity, tracked persons, low / high EasyControl setpoints, Boost and override durations, bedroom pre-bed window. |
| Boiler call and alert thresholds | Debounce, backoff, demand hysteresis, alert thresholds, battery %. |
| Gas report settings | Gas meter entity, outdoor sensor, heating-degree-day base (default 18 °C). |

Schedule text: one comfort window per line, e.g.

```
daily 06:00-23:00
mon,wed,fri 08:00-17:00
mon-fri 07:00-09:00
```

Defaults: living area 06:00–23:00; working room Mon/Wed/Fri 08:00–17:00; bedroom follows work hours plus a pre-bed warm-up (default 21:30–22:30).

Changes apply without restarting Home Assistant.

## Entities

Per room (`<domain>.smart_heating_<room>[_<key>]`): a read-only `climate`, sensors for *reason* (machine value), *summary* (plain sentence, e.g. "Warm from 17:00"), *next change* and *lead time*, Boost and cancel-boost `button`s. System-wide: a Vacation `switch` and days `number`, and Manual-room override start and cancel `button`s. Status entities: `sensor.smart_heating_status`, `sensor.smart_heating_active_alerts` (count, plain-language `messages` attribute), `binary_sensor.smart_heating_boiler_call` and `sensor.smart_heating_boiler_*` (`demand_rooms`, `target`, `last_write`, `write_result`, `backoff`, `manual_hold`).

## Dashboard

On setup the integration writes `smart_heating_dashboard.yaml` into your Home Assistant config folder and registers it as a **Smart Heating** dashboard in the sidebar. Nothing to configure. Pages: **Overview** (status, boiler, alerts when there are any, controls), **Rooms** (one section per room with a 24 hour temperature graph and, secondary, the radiator valve's battery and valve opening, assumed to be `sensor.<name>_battery`, `number.<name>_valve_position`, `sensor.<name>_pi_heating_demand`) and **Help**. Schedules are edited through the integration's Configure dialog (linked from the dashboard).

The registration uses Home Assistant internals, so if it ever fails (see the log) register the file by hand in `configuration.yaml`:

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

## How decisions are made

Target precedence per room: **Boost > open-window pause > Vacation > Away > schedule (with pre-heat; skipped while the room's occupants are away) > setback**. The boiler is called only for rooms whose target is comfort and whose temperature is below it by more than the hysteresis. All decision logic lives in a pure Python engine (`custom_components/smart_heating/engine/`) with no Home Assistant imports, tested with a fake clock. See `GLOSSARY.md`, `docs/adr/` and `docs/design.md`.

## If you change something by hand

- **Radiator valve (TRV):** a temperature you set on the valve stays until that room's target next changes (for example when its schedule moves on); then the integration takes over again.
- **Lost TRV writes:** if the valve never took the temperature we sent, it is sent again (up to 3 times); if it still does not accept it you get an alert.
- **EasyControl:** a temperature you set on the EasyControl is respected for 2 hours (configurable under advanced settings). After that the integration resumes and sets the temperature it wants.

## Assumptions

The Bosch cloud and Zigbee timing could not be measured, so defaults were assumed and are all configurable: debounce 5 min, max one write per 2 min, 429 backoff 5→30 min, a hand change on the EasyControl respected for 2 h, a TRV write checked after 10 min, default pre-heat lead time 70 min. Details and how to verify each in `docs/research/phase0-findings.md`. Probe scripts to measure them live are in `scripts/phase0/`.

## License

[MIT](LICENSE)

## Development

```bash
python -m venv .venv && .venv/bin/pip install -r requirements-test.txt
.venv/bin/pytest -q
```

## Troubleshooting

- *Boiler never fires*: check the EasyControl entity is set under *Boiler and presence settings*, and the Bosch integration can write setpoints; look for `bosch_outage` / rate-limit alerts.
- *Room ignores external sensor*: readings older than 60 min fall back to the TRV sensor plus offset; a sensor silent for 2 h raises an alert.
- Please open an [issue](https://github.com/stijnb1234/ha-smart-thermostat/issues) with debug logs (`custom_components.smart_heating: debug`).
