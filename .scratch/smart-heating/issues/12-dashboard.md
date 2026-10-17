# 12: Dashboard

**What to build:** A dashboard shows each Room's state, target, why it is heating and next change, and edits schedules, Boost, Vacation mode and Manual-room override.

**Blocked by:** 04, 05, 06

**Status:** resolved

- [ ] Per-Room state with reason visible
- [ ] Schedules, Boost, Vacation mode and Manual-room override usable from the dashboard (Boost, Vacation, Manual-room override: yes. Schedules: NOT editable on the dashboard; see limitation below)

Parent spec: `.scratch/smart-heating/spec.md`

## Answer

Limitation (review): the per-Room climate entities are read-only (targets come from schedule/Boost/Away/Vacation), and schedules are edited in the integration's options flow, which the dashboard only links to (markdown card). Standard Lovelace cards cannot edit free-form schedules (ADR-0005). The second checkbox is therefore left unticked; first box is ticked as written. Boost/Manual-room override durations and the pre-bed window are options-flow settings too.

Resolved on branch `ticket-12`. Decision recorded in `docs/adr/0005-dashboard-standard-lovelace-cards.md`: generated standard Lovelace cards, no custom JS.

- Closed the gap that nothing ran `decide()`: `coordinator.py` (thin `DataUpdateCoordinator`, 60 s) builds a `Snapshot` from HA states and runs the pure `controller.py` (`Controller.step` / `confirm`): temperature history, unmet tracking for `target_not_reached`, learned lead times, warm-up recording (`warmup.py`) into the learner, last-commands and `window_paused_until` feedback. Then it applies via `trv_adapter`, `easycontrol_adapter`, `alerts_adapter`; presence via `presence_adapter`; vacation from `vacation.py`; Boosts and Manual-room override from `hass.data`.
- Pure `explain.py` (reason: boost/window/vacation/away/pre_heat/schedule/setback, plus next change and its target); `engine.wants_comfort` made public for it.
- Entities: per-Room `climate` (read-only), sensors reason / next change / lead time, plus existing Boost and Manual-room override buttons, Vacation switch and number (new `number.py`, `switch.py` platforms).
- `dashboard.py` generates the dashboard (per-room status and Boost, Vacation, Manual-room override, options-flow link for schedules), written to `<config>/smart_heating_dashboard.yaml`.
- New options step "Boiler and presence settings": EasyControl entity, tracked persons, low/high EasyControl setpoints (defaults 15/22).
- Tests: `tests/glue/`. Not verified in a real HA: all glue (coordinator, climate, sensor, number, switch, options step), entity-id predictability, dashboard rendering, Z2M name/battery entity assumptions (`climate.<name>` object id, `sensor.<name>_battery`).
