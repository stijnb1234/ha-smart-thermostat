# Home Assistant heating integrations: research notes

Researched 2026-10-17. Primary sources only; each claim carries its source inline. Items marked **[UNVERIFIED]** could not be confirmed from a primary source.

Scope correction applied: (1) EasyControl is controlled via the user's own custom integration `stijnb1234/ha-bosch-pointt`; (2) the Shelly BLU TRVs are paired directly to Zigbee2MQTT (Z2M), not through the HA Shelly integration.

Repo refs: `P` = https://github.com/stijnb1234/ha-bosch-pointt (default branch HEAD, raw files under https://raw.githubusercontent.com/stijnb1234/ha-bosch-pointt/HEAD/).

---

## 1. Bosch EasyControl (CT200) in Home Assistant

### 1.1 Which integration

- HA core `bosch_shc` does **not** cover EasyControl. Its docs say it supports devices connected to a Bosch Smart Home Controller (contacts, detectors, thermostats and room thermostats, plugs, etc.), communicating locally with the SHC, and the page never mentions EasyControl. Source: https://www.home-assistant.io/integrations/bosch_shc/
- The HACS `bosch` integration (`bosch-thermostat/home-assistant-bosch-custom-component`, built on `bosch-thermostat-client-python`) lists "EASYCONTROL (XMPP only): Bosch CT200" and says "XMPP -> connect to bosch cloud", HTTP is local and "available only for IVT devices". Source: https://raw.githubusercontent.com/bosch-thermostat/home-assistant-bosch-custom-component/master/README.md. The client library README says supported protocols are HTTP and XMPP and both are "still in development": https://github.com/bosch-thermostat/bosch-thermostat-client-python
  - The user's own README calls the XMPP route a "dead-end" for this unit (`archive_legacy_xmpp/` kept "for the reasoning trail"), and credits the Nefit Easy integration as the "older, now-incompatible XMPP protocol". Source: P/README.md. Whether the upstream `bosch` integration works with a current CT200 firmware is **[UNVERIFIED]**; not tested.
- **Chosen path: `bosch_pointt`** (custom, HACS-installable: `hacs.json`, `manifest.json`), talking to Bosch's Pointt REST API. Source: P/README.md.

### 1.2 Transport, auth, polling

- Cloud only: `https://pointt-api.bosch-thermotechnology.com/pointt-api/api/v1`, plain HTTPS/JSON, `GET`/`PUT` on `/gateways/{serial}/resource/{path}`. No local API. Sources: P/README.md ("How it works"); P/custom_components/bosch_pointt/const.py (`API_BASE`); P/HEATING_PLAN.md section 2 ("cloud polling only ... no local API"). iot_class should therefore be `cloud_polling` (HA manifest values: https://contributors.home-assistant.io/core/integrations/manifest/).
- Auth: OAuth2 authorization_code + PKCE against SingleKey ID using the official app's `client_id` (hard-coded in `const.py`), scope `offline_access`. The login has an hCaptcha, so the refresh token is obtained by running `pointt_login.py` in a browser and pasting the token into the config flow. Source: P/README.md ("Getting a refresh token").
- Token rotation: the refresh token rotates on every use; the integration persists the new value into the config entry (`persist_refresh_token`, `async_update_entry`). Any second consumer of the same token logs the other out. There is no in-HA reauth flow if the token is revoked. Sources: P/README.md ("Known limitations", "Actions"); P/custom_components/bosch_pointt/__init__.py; P/custom_components/bosch_pointt/api.py (HTTP 400 on refresh -> `PointtAuthError`). Using the official client_id of Bosch's app is a terms-of-service/stability risk; Bosch has not documented a public API for it. **[UNVERIFIED]** whether Bosch tolerates this long-term.
- Polling: single `DataUpdateCoordinator`, `DEFAULT_SCAN_INTERVAL = 60` s, one GET per resource path sequentially (about 23 paths in `RESOURCE_PATHS`, so roughly 23 requests per poll). 404s on a path are tolerated (not every firmware exposes every resource). Sources: P/custom_components/bosch_pointt/const.py and `__init__.py`.
- **Rate limits: [UNVERIFIED].** No Bosch documentation or response header handling was found in the repo or elsewhere; the repo has no 429 handling. Design should self-limit writes (the plan proposes at most one write per 2 minutes, P/HEATING_PLAN.md section 6.3).

### 1.3 Entities exposed (as implemented)

Source: P/README.md "Features" table and the platform files.

| Platform | Entities |
|---|---|
| `climate` | "Thermostat": current temp (`zones/zn1/temperatureActual`), target (`zones/zn1/temperatureHeatingSetpoint`), HVAC modes AUTO (device `clock`) / HEAT (device `manual`), 5-30 C, step 0.5 |
| `sensor` | Outdoor Temperature, Indoor Humidity, Firmware Version, Hot Water System, System Pressure, Burner Modulation, Active Notifications; diagnostic Zone Status, Heating Control |
| `binary_sensor` | Refill Needed, Burner Active |
| `switch` | Away Mode, Fireplace Mode, Child Lock, Extra Hot Water (disabled by default), Notification Light |
| `number` | Away Mode Temperature, Open Window Detection Temperature, Outdoor Sensor Offset (-2..2) |
| Actions | `bosch_pointt.get_resource`, `bosch_pointt.put_resource` (raw path read/write) |

Not exposed: flow/return temperatures, boiler fault codes (P/README.md "Known limitations").

### 1.4 What HA can write

- **Setpoint:** `async_set_temperature` PUTs to `zones/zn1/clockOverride/temperatureHeating` (a temporary override on top of the weekly program), regardless of mode. Source: P/custom_components/bosch_pointt/climate.py. In the API dump, `temperatureHeatingSetpoint` itself is `writeable:0`, while `clockOverride/temperatureHeating` is `writeable:1`, min 0 max 30 step 0.5 and reads `0.0` when no override is active. Source: https://raw.githubusercontent.com/stijnb1234/ha-bosch-pointt/HEAD/bosch_api_reference.txt
- **Mode:** `zones/zn1/userMode` is writable with `"clock"` / `"manual"` (confirmed via mitmproxy capture per code comment). Source: climate.py, bosch_api_reference.txt.
- **Manual-mode setpoint resource:** which resource holds the manual setpoint is **[UNVERIFIED]**; it is open question P1 in P/docs/PHASE0_PROBES.md and P/HEATING_PLAN.md section 14 (candidate `zones/zn1/manualTemperatureHeating`, unconfirmed). The current climate entity in manual mode therefore still writes `clockOverride/...`, which is not confirmed to act as the manual setpoint. Persistence of a manual setpoint over hours/reboot (P2) is also unverified.
- **Schedule:** `programs/pg1/week` is `type: weekProgram`, `writeable:1`; entries are `{d, t (minutes from midnight), Th (temp), name}`. Readable and (per the API flag) writable through `put_resource`; no entity wraps it. Write format is untested (**[UNVERIFIED]**). Source: bosch_api_reference.txt.
- Writes are followed by `coordinator.async_request_refresh()`, but the device may report the old value for a while (comment in `put_resource`: "May still show the old value if the device hasn't applied the write yet").

### 1.5 High setpoint as a boiler call-for-heat

- Mechanism: `heatingCircuits/hc1/control = room`, i.e. the boiler is room-temperature led: it fires only when the EasyControl setpoint exceeds the room temperature it measures, and flow temperature scales with the difference. Source: P/HEATING_PLAN.md section 2 (derived from the API; `control` writeable flag is 1 but allowed values are unverified, probe P6).
- The plan states the route "is proven to fire the boiler" (P/HEATING_PLAN.md D8) via the clock-override write, and the `burner_active` binary sensor and `heatSources/modulation` let you observe it.
- **Latency write -> burner firing is not measured yet** (probe P4 table cell is empty in HEATING_PLAN.md section 14). Lower bound: up to one cloud round trip plus the device's own sync; the 60 s poll adds up to 60 s of read-back delay (or ~immediate with the post-write refresh). Treat as **[UNVERIFIED]**, measure with P4.
- Caveat: only one zone sensor (living room) is the reference, so a bump must be set above the living-room actual (plan algorithm in section 6.3).

### 1.6 Reliability caveats

Summarised from P/README.md and P/HEATING_PLAN.md: cloud dependency (internet/Bosch outage means writes fail, EasyControl keeps its last setpoint); token revocation requires manual re-login; tested on a single CT200 (firmware 05.04.00, "RRC 2.0"); API is reverse-engineered, so Bosch can change it without notice.

---

## 2. Shelly BLU TRV via Zigbee2MQTT

### 2.1 Support status (confirmed)

- Zigbee2MQTT has a device page for **Shelly SBTR-001AEU "Thermostatic radiator valve"**. Source: https://www.zigbee2mqtt.io/devices/SBTR-001AEU.html
- The converter in zigbee-herdsman-converters matches `zigbeeModel: ["BLU TRV"]`, `model: "SBTR-001AEU"`. Source: https://github.com/Koenkk/zigbee-herdsman-converters/blob/master/src/devices/shelly.ts (read 2026-10-17; the definition block near line 3408).
- So the device does speak Zigbee (the Zigbee firmware mode of the Gen3 BLU TRV) and is handled by Z2M; this is distinct from the Bluetooth/BLU Gateway route documented in the HA Shelly integration (https://www.home-assistant.io/integrations/shelly/, which only briefly lists BLU TRV "via Shelly BLU Gateway Gen3" and gives no entity detail). Whether the user's unit being the "Gen3 variant" maps to this exact model ID is taken from the user's statement; the converter does not distinguish variants **[UNVERIFIED]**.
- Z2M page note: connect Shelly devices via WiFi/Bluetooth to update firmware "until they gain support for OTA updates over Zigbee". The user's plan records firmware >= 1.5.0 via the Shelly app (BLE) (P/HEATING_PLAN.md section 7.1 and probe P8). The Shelly firmware-version requirement itself is not stated on the Z2M page **[UNVERIFIED from vendor docs]**.

### 2.2 Exposes (Z2M device page + converter source)

Sources: https://www.zigbee2mqtt.io/devices/SBTR-001AEU.html and the converter `shelly.ts` above.

| Need | Z2M property | Notes |
|---|---|---|
| Measured room temp (TRV sensor) | `local_temperature` | readable (`/get`) |
| Target temperature | `occupied_heating_setpoint` | 4-30 C, step 0.1 |
| Alternate target | `unoccupied_heating_setpoint` | selected when `external_occupancy` is false |
| Mode | `system_mode` | `off`, `auto`, `heat` |
| Valve opening / heat demand | `pi_heating_demand` (0-100 %, read-only) and `valve_position` (0-100 %, read/write, manufacturer cluster 0xFC24) | `valve_position` reporting configured min 10 s, max 1 h, change 1 in the converter |
| Manual valve override | `manual_mode` (0 = auto, 1 = manual) | custom cluster attribute |
| External temperature input | `external_temperature` (-40..85 C, step 0.01, write-only: cannot `/get`) | see 2.3 |
| External occupancy | `external_occupancy` (binary, write) | |
| Calibration offset | `local_temperature_calibration` (-10..10, step 0.1) | |
| Valve calibration | `calibrate` = `trigger`; `calibration_ok` binary diagnostic | |
| Setpoint limits | `min_heat_setpoint_limit`, `max_heat_setpoint_limit` (4-30) | |
| Battery | `battery` (%) | via `m.battery()` |
| Identify | `identify` | |

**Not exposed in Z2M (confirmed by absence in page and converter):** open-window detection, boost, on-device schedules, `running_state`/hvac_action. (The plan's D7 notes the TRV exposes no `running_state`, consistent with this.) The HA Shelly-integration docs likewise do not mention these for BLU TRV.

### 2.3 External temperature behaviour (from the converter)

- Writing `external_temperature` sets the Thermostat cluster `remoteSensing` bit 0 and sends the value as an attribute report of `msTemperatureMeasurement` (`shellyTRVEnableRemoteTemperature`, `shellyTRVSendExternalTemperature`).
- The device is battery powered/sleepy, so delivery is tracked: the request is persisted in device meta, retried when the TRV next reports (min retry interval 1.5 s), up to 30 attempts or 1 hour (`SHELLY_TRV_EXTERNAL_TEMPERATURE_MAX_ATTEMPTS = 30`, `..._MAX_AGE_MS = 1 h`), confirmed when `localTemp` equals the requested value, and also retried on `deviceAnnounce`. So an external temperature may take until the next wake window to be applied, and is dropped with a warning if not confirmed within an hour.
- Consequence: `local_temperature` reflects the pushed value once confirmed (the converter confirms against `localTemp`). Fallback timeout when pushes stop (does the TRV return to its own sensor?) is **[UNVERIFIED]**; it is probe P7 in P/docs/PHASE0_PROBES.md.

### 2.4 Update rate and latency

- Only `valve_position` has explicit reporting config in the converter (10 s .. 1 h, change 1). Reporting for `local_temperature` / `pi_heating_demand` uses the `m.thermostat` defaults; exact intervals are **[UNVERIFIED]** here. The user's probe P8 plans Z2M reporting overrides (min 10 s, max 300 s, change 1) (P/docs/PHASE0_PROBES.md).
- Setpoint writes to a sleepy device are delivered when the device polls/wakes; latency is not documented by Z2M or Shelly for this model **[UNVERIFIED]**. Measure.
- HA side: with Z2M's MQTT discovery these appear as a `climate`, `sensor` (battery, valve position), `number`, and `select`/`button` entities; exact HA entity mapping was not verified from the Z2M HA-integration source **[UNVERIFIED]**. Probe P7 step 1 checks whether `number.*_external_temperature` exists, else publish to `zigbee2mqtt/<name>/set`.

---

## 3. Custom integration best practice

### 3.1 Structure

Layout for a HACS custom integration (one integration per repo, in `custom_components/<domain>/`, https://hacs.xyz/docs/publish/integration):

```
custom_components/<domain>/
  __init__.py        # async_setup_entry / async_unload_entry, coordinator creation, platform forwarding
  manifest.json
  config_flow.py     # ConfigFlow + OptionsFlow
  coordinator.py     # DataUpdateCoordinator subclass(es)
  const.py
  climate.py sensor.py switch.py number.py ...
  store.py           # Store wrapper for learned data
  strings.json / translations/en.json
  services.yaml
hacs.json
brand/icon.png (HACS requires brand assets; see below)
tests/
```

- **manifest.json:** for custom integrations `version` is required (SemVer or CalVer); `iot_class` one of `local_polling, local_push, cloud_polling, cloud_push, assumed_state, calculated`; integrations with a config flow must set `integration_type` (default `hub`, `device`/`service`/`helper` for single-device/service/helper) and `config_flow: true`. Source: https://contributors.home-assistant.io/core/integrations/manifest/. HACS additionally requires `domain, documentation, issue_tracker, codeowners, name, version` (https://hacs.xyz/docs/publish/integration). Note: `ha-bosch-pointt` is `cloud_polling`; its `manifest.json` was not independently audited for these keys here.
- **Config flow:** class-based `ConfigFlow`; test credentials before creating the entry, set a unique ID (quality-scale rules `config-flow`, `test-before-configure`, `unique-config-entry`, listed in the developer docs sidebar: https://contributors.home-assistant.io/core/integrations/manifest/ nav; rules index at https://developers.home-assistant.io/docs/core/integration-quality-scale/rules **[page not fetched, rule names read from site nav]**).
- **Options flow:** static `@callback async_get_options_flow` on the config flow returning the options flow; start at `async_step_init`; read `self.config_entry`; `async_create_entry(data=...)` writes `entry.options`. Subclass `OptionsFlowWithReload` to reload the entry on change; or subclass `OptionsFlow` and register `entry.add_update_listener(...)`; do not combine both. Source: https://contributors.home-assistant.io/core/integrations/options-flow/
- **DataUpdateCoordinator:** one coordinator polls once for all entities; do first refresh during setup (`async_config_entry_first_refresh`); entities extend `CoordinatorEntity`; skip updates that change nothing; "push with a coordinator" is also supported. Source: https://developers.home-assistant.io/docs/integration_fetching_data (headings read; page content fetched via nav only, detail **[partially UNVERIFIED]**). Reference implementation in the user's repo: `BoschPointtCoordinator` in P/custom_components/bosch_pointt/__init__.py (note: a rotated refresh token is persisted from inside the coordinator).
- **Platforms:** forward with `hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)`; climate entity docs: https://developers.home-assistant.io/docs/core/entity/climate. For a heating-demand controller, expose settable parameters as `number`/`switch`/`select` entities (as the plan proposes) so they are tunable from the UI.
- **Store for persisted learning data:** `homeassistant.helpers.storage.Store(hass, version, key, *, minor_version=..., ...)`; `async_load()` returns `None` if missing (corrupt JSON is renamed to `.corrupt.<timestamp>` and returns `None`); `async_save(data)` writes immediately; `async_delay_save(data_func, delay)` coalesces repeated saves (takes a callable); version/minor_version are stored and a mismatch triggers `_async_migrate_func` (override in a subclass), raising `UnsupportedStorageVersionError` if newer than `max_readable_version`. Source: https://raw.githubusercontent.com/home-assistant/core/dev/homeassistant/helpers/storage.py. Use Store for learned model data, config entry data/options for user settings and credentials.
- **Tests:** `pytest-homeassistant-custom-component` extracts HA's test plugins: `hass` and other core fixtures, `MockConfigEntry` from `pytest_homeassistant_custom_component.common`, the `enable_custom_integrations` fixture is required, `asyncio_mode = auto`, fixtures files under `tests/fixtures` via `load_fixture`, syrupy snapshots need `HomeAssistantSnapshotExtension`. Package versions track HA core releases. Source: https://github.com/MatthewFlamm/pytest-homeassistant-custom-component. The user's repo has no tests yet in the tree listing (tree checked 2026-10-17: no `tests/` directory).

### 3.2 HACS packaging

Source: https://hacs.xyz/docs/publish/integration
- One integration per repository, under `custom_components/<name>/`; `hacs.json` at repo root (`content_in_root` for root layouts).
- manifest keys `domain, documentation, issue_tracker, codeowners, name, version`.
- Brand assets required: a `brand/` directory with at least `icon.png`.
- GitHub releases preferred (users see the 5 latest plus default branch); without releases HACS uses default-branch files. HACS GitHub Actions validation exists on a separate page (not fetched; the bosch repo uses `.github/workflows/hacs.yaml` and `validate.yaml` per its tree).

### 3.3 Dashboard options

1. **Standard cards, zero frontend code:** thermostat card plus entities/history-graph cards over the integration's entities. Docs: https://www.home-assistant.io/dashboards/
2. **Custom Lovelace card:** a JS custom element (class extends `HTMLElement`, `customElements.define`), with `setConfig(config)` (throw on invalid), a `hass` setter called on state changes, `getCardSize()`; shipped as a JS module and registered as a dashboard resource (e.g. `/local/...js`, type JavaScript module). Source: https://contributors.home-assistant.io/frontend/custom-ui/card/. `window.customCards` registration for the card picker is **[UNVERIFIED]** (not mentioned on that page).
3. **Custom panel (sidebar page):** the element receives `hass`, `narrow`, `route`, `panel` (config in `panel.config`). From Python an integration calls `async_register_panel()` from the `panel_custom` integration (options `webcomponent_name`, `frontend_url_path`, `sidebar_title`, `module_url`, `require_admin`, ...); YAML `panel_custom` is the non-integration route. Sources: https://contributors.home-assistant.io/frontend/custom-ui/panel/ and https://www.home-assistant.io/integrations/panel_custom
4. Serving the JS from the integration (static path registration) avoids asking users to add a resource manually; the exact API (`hass.http.async_register_static_paths`) is **[UNVERIFIED]**, not fetched.

---

## Implications for design

1. **Central heat-demand logic belongs in the integration** (matches plan D3): the integration alone knows what it wrote vs. what a human dialled; coordinator is the right place to detect dial changes and enforce write rate limits (cloud polling at 60 s, rate limits unknown, so self-limit to one write per 2 minutes and never write unchanged values).
2. **Unresolved EasyControl write path:** current `set_temperature` writes `clockOverride/temperatureHeating`, while the plan wants `manual` mode with one setpoint. Resolve probes P1-P4 first (manual setpoint resource, persistence, dial behaviour, write-to-burner latency) before building the demand controller on `manual`. Fallback: keep `clock` mode and use clockOverride (known to fire the boiler).
3. **Token risk:** one refresh-token consumer only, persisted on every rotation; add a reauth flow (HA `reauthentication-flow` quality rule) and a repair issue because revocation is currently unrecoverable in-HA.
4. **TRV signals:** use `pi_heating_demand` (read-only, 0-100 %) as the demand source; `valve_position` is a separate writable manual override and `manual_mode` disables automatic regulation; avoid writing it. There is no `running_state` or window-open/boost entity in Z2M, so implement boost and window logic in HA if wanted.
5. **External temperature push:** `external_temperature` is write-only, delivered asynchronously to a sleepy device with retries up to 1 hour. Keep a heartbeat (plan: 10 min), do not rely on read-back via `/get`, and treat `local_temperature` change as the confirmation. Fallback timeout is unknown (P7); keep an explicit stale-sensor policy.
6. **Persisted learning data** goes in a `Store` (versioned, with a migration hook, `async_delay_save` to coalesce writes); user-tunable thresholds in options flow + `number` entities.
7. **Tests:** add `tests/` using pytest-homeassistant-custom-component with a mocked `PointtApi`; test coordinator logic (hysteresis, write throttling, manual-change detection) as pure functions.
8. **Dashboard:** start with standard cards plus diagnostic entities; add a custom panel (sidebar page registered from Python) only if a schedule/overview editor is needed; a custom card suits a compact per-room widget.

## Blockers / gaps

- No Bosch documentation on Pointt rate limits, token lifetime guarantees, or write latency exists in primary sources found; all need empirical probes (P1-P4 in the user's `docs/PHASE0_PROBES.md`).
- Z2M reporting intervals and sleepy-device command latency for SBTR-001AEU are undocumented; external temperature fallback timeout unknown.
- developers.home-assistant.io pages now 301-redirect to contributors.home-assistant.io; quality-scale rule contents and the coordinator page body were not read in full.
