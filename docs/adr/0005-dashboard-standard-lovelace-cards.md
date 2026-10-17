# Dashboard is generated standard Lovelace cards, no custom JS

The spec left the dashboard form open (standard cards, custom card, custom panel). We generate a Lovelace dashboard config from the configured Rooms using only built-in cards (`entities`, `markdown`), and write it to `<config>/smart_heating_dashboard.yaml` on setup. The user registers it once as a YAML-mode dashboard (`lovelace: dashboards:` in `configuration.yaml`, `filename: smart_heating_dashboard.yaml`).

Entity ids are fixed by the integration (`<domain>.smart_heating_<room>[_<key>]`), so the generated config can reference them. Schedule editing is a link to the integration's options flow, which is already the validated editor for Rooms (ADR-0001); no schedule editor is duplicated in the UI.

## Consequences

- No frontend build, no JS to maintain; HA upgrades cannot break a custom card.
- The dashboard is regenerated at each setup, so Room changes appear after the options-flow reload (the YAML dashboard reloads on browser refresh).
- Schedules are not editable inline; the markdown card links to Configure.
- Entity ids are set explicitly; if a user renames one in the registry, the generated dashboard will not follow.
- A custom card can replace this later without touching the entities.
