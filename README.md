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
- **Away / Vacation**: everyone away drops rooms to setback; long absence or Vacation mode holds frost-hold and returns before you arrive.
- **Boost** buttons per room and a **Manual-room override** for rooms with dumb radiator valves.
- **Alerts** (TRV offline, low battery, room never reaches target, Bosch outage, stale sensor) and a **weekly gas report** (m³ per heating-degree-day vs last year).
- A generated **dashboard** showing each room's state, target, why it is heating and the next change.

Not controlled: floor heating, dumb TRVs (except through the Manual-room override), door-aware zones. See `.scratch/smart-heating/spec.md`.

## Requirements

- Home Assistant 2024.6 or newer.
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

Per room (`<domain>.smart_heating_<room>[_<key>]`): a read-only `climate`, sensors for *reason*, *next change* and *lead time*, and a Boost `button`. System-wide: a Vacation `switch` and days `number`, and a Manual-room override `button`.

## Dashboard

On setup the integration writes `smart_heating_dashboard.yaml` into your Home Assistant config folder. Register it once in `configuration.yaml`:

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

Restart, and a *Smart Heating* entry appears in the sidebar. Schedules are edited through the integration's Configure dialog (linked from the dashboard).

## How decisions are made

Target precedence per room: **Boost > open-window pause > Vacation > Away > schedule (with pre-heat) > setback**. The boiler is called only for rooms whose target is comfort and whose temperature is below it by more than the hysteresis. All decision logic lives in a pure Python engine (`custom_components/smart_heating/engine/`) with no Home Assistant imports, tested with a fake clock. See `GLOSSARY.md`, `docs/adr/` and `docs/design.md`.

## Assumptions

The Bosch cloud and Zigbee timing could not be measured, so defaults were assumed and are all configurable: debounce 5 min, max one write per 2 min, 429 backoff 5→30 min, setpoint re-asserted after 30 min of drift, default pre-heat lead time 70 min. Details and how to verify each in `docs/research/phase0-findings.md`. Probe scripts to measure them live are in `scripts/phase0/`.

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
