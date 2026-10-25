"""Thin HA glue: config flow creates the entry, options flow edits Rooms.

All validation and mapping lives in rooms.py (pure, unit-tested).
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_ARRIVAL_ENTITIES,
    CONF_AUTO_ARRIVAL,
    CONF_BACKOFF_BASE_MINUTES,
    CONF_BACKOFF_MAX_MINUTES,
    CONF_BATTERY_LOW_PERCENT,
    CONF_BOILER_ENTITY,
    CONF_BOILER_HIGH,
    CONF_BOILER_LOW,
    CONF_BOILER_MANUAL_HOLD_MINUTES,
    CONF_BOILER_SETTLE_MINUTES,
    CONF_BOOST_MINUTES,
    CONF_DEBOUNCE_MINUTES,
    CONF_DEMAND_HYSTERESIS,
    CONF_GAS_ENTITY,
    CONF_HDD_BASE,
    CONF_MANUAL_OVERRIDE_MINUTES,
    CONF_NOTIFY_DELAY_MINUTES,
    CONF_NOTIFY_TARGETS,
    CONF_OUTAGE_FAILURES,
    CONF_OUTDOOR_ENTITY,
    CONF_PERSONS,
    CONF_PRE_BED_END,
    CONF_PRE_BED_START,
    CONF_ROOMS,
    CONF_SENSOR_STALE_HOURS,
    CONF_TARGET_WINDOW_HOURS,
    CONF_TRV_OFFLINE_MINUTES,
    CONF_TRV_SETTLE_MINUTES,
    CONF_VACATION_CALENDAR,
    CONF_VACATION_KEYWORDS,
    CONF_Z2M_BASE_TOPIC,
    DEFAULT_AUTO_ARRIVAL,
    DEFAULT_BOILER_HIGH,
    DEFAULT_BOILER_LOW,
    DEFAULT_BOOST_MINUTES,
    DEFAULT_MANUAL_OVERRIDE_MINUTES,
    DEFAULT_NOTIFY_DELAY_MINUTES,
    DEFAULT_PRE_BED_END,
    DEFAULT_PRE_BED_START,
    DEFAULT_VACATION_KEYWORDS,
    DOMAIN,
)
from .engine import (
    DEFAULT_COMFORT,
    DEFAULT_FROST_HOLD,
    DEFAULT_SETBACK,
    AlertConfig,
    EngineConfig,
    RoomConfig,
)
from .i18n import pick_language, tr
from .migration import CONFIG_VERSION
from .report import DEFAULT_HDD_BASE
from .rooms import (
    PRESETS,
    RoomError,
    add_room,
    format_schedule,
    remove_room,
    replace_room,
    room_from_form,
)
from .trv_devices import DEFAULT_Z2M_BASE_TOPIC

REPORT_KEYS = (CONF_GAS_ENTITY, CONF_OUTDOOR_ENTITY, CONF_HDD_BASE)
HEATING_KEYS = (
    CONF_BOILER_ENTITY,
    CONF_PERSONS,
    CONF_AUTO_ARRIVAL,
    CONF_ARRIVAL_ENTITIES,
    CONF_VACATION_CALENDAR,
    CONF_VACATION_KEYWORDS,
    CONF_BOILER_LOW,
    CONF_BOILER_HIGH,
    CONF_BOOST_MINUTES,
    CONF_MANUAL_OVERRIDE_MINUTES,
    CONF_PRE_BED_START,
    CONF_PRE_BED_END,
)
ADVANCED_KEYS = (
    CONF_DEBOUNCE_MINUTES,
    CONF_BACKOFF_BASE_MINUTES,
    CONF_BACKOFF_MAX_MINUTES,
    CONF_DEMAND_HYSTERESIS,
    CONF_BOILER_MANUAL_HOLD_MINUTES,
    CONF_BOILER_SETTLE_MINUTES,
    CONF_TRV_SETTLE_MINUTES,
    CONF_TRV_OFFLINE_MINUTES,
    CONF_TARGET_WINDOW_HOURS,
    CONF_OUTAGE_FAILURES,
    CONF_SENSOR_STALE_HOURS,
    CONF_BATTERY_LOW_PERCENT,
    CONF_NOTIFY_TARGETS,
    CONF_NOTIFY_DELAY_MINUTES,
    CONF_Z2M_BASE_TOPIC,
)
SETTING_KEYS = REPORT_KEYS + HEATING_KEYS + ADVANCED_KEYS


class SmartHeatingConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = CONFIG_VERSION

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return SmartHeatingOptionsFlow()

    async def async_step_user(self, user_input=None):
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        if user_input is not None:
            return self.async_create_entry(title="Smart Heating", data={}, options={CONF_ROOMS: []})
        return self.async_show_form(step_id="user")


def _temp(default: float) -> tuple[Any, Any]:
    return (
        selector.NumberSelector(
            selector.NumberSelectorConfig(min=5, max=30, step=0.5, unit_of_measurement="°C")
        ),
        default,
    )


def _number(min_: float, max_: float, step: float, unit: str | None = None) -> Any:
    # NumberSelectorConfig rejects an explicit unit_of_measurement=None, so only pass it when set.
    box = selector.NumberSelectorMode.BOX
    if unit is None:
        return selector.NumberSelector(selector.NumberSelectorConfig(min=min_, max=max_, step=step, mode=box))
    return selector.NumberSelector(
        selector.NumberSelectorConfig(min=min_, max=max_, step=step, mode=box, unit_of_measurement=unit)
    )


def _room_schema(room: dict[str, Any] | None, default_preset: str = "none") -> vol.Schema:
    room = room or {}
    engine_defaults = RoomConfig(name="")

    def opt(key, default=None):
        value = room.get(key, default)
        return vol.Optional(key, description={"suggested_value": value})

    comfort, _ = _temp(DEFAULT_COMFORT)
    return vol.Schema(
        {
            vol.Required("name", description={"suggested_value": room.get("name")}): str,
            opt("manual", False): selector.BooleanSelector(),
            opt("floor_heating", False): selector.BooleanSelector(),
            opt("open_radiators", False): selector.BooleanSelector(),
            opt("trv_entity"): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="climate")
            ),
            opt("sensor_entity"): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="temperature")
            ),
            opt("presence_entities"): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain=["person", "device_tracker", "binary_sensor", "input_boolean", "switch"],
                    multiple=True,
                )
            ),
            opt("arrival_entities"): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain=["zone", "person", "device_tracker", "binary_sensor", "input_boolean", "switch"],
                    multiple=True,
                )
            ),
            opt("comfort", DEFAULT_COMFORT): comfort,
            opt("setback", DEFAULT_SETBACK): comfort,
            opt("frost_hold", DEFAULT_FROST_HOLD): comfort,
            opt("preset", default_preset): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=list(PRESETS), translation_key="preset", mode=selector.SelectSelectorMode.DROPDOWN
                )
            ),
            opt("schedule_text", format_schedule(room.get("schedule", []))): selector.TextSelector(
                selector.TextSelectorConfig(multiline=True)
            ),
            opt("trv_offset", engine_defaults.trv_offset): _number(-5, 5, 0.1, "°C"),
            opt(
                "lead_time_minutes", engine_defaults.lead_time.total_seconds() / 60
            ): _number(0, 480, 5, "min"),
            opt("compensate_trv", engine_defaults.compensate_trv): selector.BooleanSelector(),
            opt("window_detection", engine_defaults.window_detection): selector.BooleanSelector(),
            opt("window_drop", engine_defaults.window_drop): _number(0.5, 10, 0.1, "°C"),
            opt(
                "window_pause_minutes", engine_defaults.window_pause.total_seconds() / 60
            ): _number(15, 30, 1, "min"),
        }
    )


class SmartHeatingOptionsFlow(config_entries.OptionsFlow):
    """Add, edit and remove Rooms. Saved when the user picks 'Save and close'."""

    def __init__(self) -> None:
        self._rooms: list[dict[str, Any]] | None = None
        self._editing: str | None = None
        self._settings_cache: dict[str, Any] | None = None

    @property
    def _settings(self) -> dict[str, Any]:
        if self._settings_cache is None:
            opts = self.config_entry.options
            self._settings_cache = {k: opts[k] for k in SETTING_KEYS if k in opts}
        return self._settings_cache

    @_settings.setter
    def _settings(self, value: dict[str, Any]) -> None:
        self._settings_cache = value

    def _room_from_input(self, user_input: dict[str, Any]) -> dict[str, Any]:
        pre_bed = (
            self._settings.get(CONF_PRE_BED_START, DEFAULT_PRE_BED_START),
            self._settings.get(CONF_PRE_BED_END, DEFAULT_PRE_BED_END),
        )
        return room_from_form(user_input, pre_bed)

    @property
    def rooms(self) -> list[dict[str, Any]]:
        if self._rooms is None:
            self._rooms = [dict(r) for r in self.config_entry.options.get(CONF_ROOMS, [])]
        return self._rooms

    def _reason(self, err: RoomError) -> str:
        return tr(pick_language(self.hass.config.language), f"room_error.{err.code}", **err.params)

    async def async_step_init(self, user_input=None):
        options = ["add_room"]
        if self.rooms:
            options += ["edit_room", "remove_room"]
        options += ["heating_settings", "advanced_settings", "report_settings", "save"]
        return self.async_show_menu(step_id="init", menu_options=options)

    async def async_step_report_settings(self, user_input=None):
        current = self._settings
        if user_input is not None:
            self._settings = {
                **{k: v for k, v in self._settings.items() if k not in REPORT_KEYS},
                **{k: v for k, v in user_input.items() if v not in (None, "")},
            }
            return await self.async_step_init()

        def opt(key, default=None):
            return vol.Optional(key, description={"suggested_value": current.get(key, default)})

        schema = vol.Schema(
            {
                opt(CONF_GAS_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor", device_class="gas")
                ),
                opt(CONF_OUTDOOR_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor", device_class="temperature")
                ),
                opt(CONF_HDD_BASE, DEFAULT_HDD_BASE): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=10, max=25, step=0.5, unit_of_measurement="°C")
                ),
            }
        )
        return self.async_show_form(step_id="report_settings", data_schema=schema)

    async def async_step_heating_settings(self, user_input=None):
        current = self._settings
        if user_input is not None:
            self._settings = {
                **{k: v for k, v in current.items() if k not in HEATING_KEYS},
                **{k: v for k, v in user_input.items() if v not in (None, [])},
            }
            if not self._settings.get(CONF_VACATION_CALENDAR):
                self._settings.pop(CONF_VACATION_CALENDAR, None)
            return await self.async_step_init()

        def opt(key, default=None):
            return vol.Optional(key, description={"suggested_value": current.get(key, default)})

        temp = selector.NumberSelector(
            selector.NumberSelectorConfig(min=5, max=30, step=0.5, unit_of_measurement="°C")
        )
        schema = vol.Schema(
            {
                opt(CONF_BOILER_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="climate")
                ),
                opt(CONF_PERSONS): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="person", multiple=True)
                ),
                opt(CONF_AUTO_ARRIVAL, DEFAULT_AUTO_ARRIVAL): selector.BooleanSelector(),
                opt(CONF_ARRIVAL_ENTITIES): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["zone", "person", "device_tracker", "binary_sensor", "input_boolean", "switch"],
                        multiple=True,
                    )
                ),
                opt(CONF_VACATION_CALENDAR): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="calendar")
                ),
                opt(CONF_VACATION_KEYWORDS, DEFAULT_VACATION_KEYWORDS): selector.TextSelector(),
                opt(CONF_BOILER_LOW, DEFAULT_BOILER_LOW): temp,
                opt(CONF_BOILER_HIGH, DEFAULT_BOILER_HIGH): temp,
                opt(CONF_BOOST_MINUTES, DEFAULT_BOOST_MINUTES): _number(5, 480, 5, "min"),
                opt(CONF_MANUAL_OVERRIDE_MINUTES, DEFAULT_MANUAL_OVERRIDE_MINUTES): _number(
                    5, 720, 5, "min"
                ),
                opt(CONF_PRE_BED_START, DEFAULT_PRE_BED_START): selector.TimeSelector(),
                opt(CONF_PRE_BED_END, DEFAULT_PRE_BED_END): selector.TimeSelector(),
            }
        )
        return self.async_show_form(step_id="heating_settings", data_schema=schema)

    async def async_step_advanced_settings(self, user_input=None):
        current = self._settings
        if user_input is not None:
            self._settings = {
                **{k: v for k, v in current.items() if k not in ADVANCED_KEYS},
                **{k: v for k, v in user_input.items() if v not in (None, "")},
            }
            return await self.async_step_init()

        def opt(key, default):
            return vol.Optional(key, description={"suggested_value": current.get(key, default)})

        engine, alerts = EngineConfig(rooms=(), boiler_low=0, boiler_high=0), AlertConfig()
        minutes = lambda td: td.total_seconds() / 60  # noqa: E731
        hours = lambda td: td.total_seconds() / 3600  # noqa: E731
        schema = vol.Schema(
            {
                opt(CONF_DEBOUNCE_MINUTES, minutes(engine.boiler_debounce)): _number(0, 60, 1, "min"),
                opt(CONF_BACKOFF_BASE_MINUTES, minutes(engine.boiler_backoff_base)): _number(1, 60, 1, "min"),
                opt(CONF_BACKOFF_MAX_MINUTES, minutes(engine.boiler_backoff_max)): _number(1, 240, 1, "min"),
                opt(CONF_DEMAND_HYSTERESIS, engine.demand_hysteresis): _number(0, 2, 0.1, "°C"),
                opt(CONF_TRV_SETTLE_MINUTES, minutes(engine.trv_settle)): _number(1, 120, 1, "min"),
                opt(CONF_BOILER_SETTLE_MINUTES, minutes(engine.boiler_settle)): _number(1, 120, 1, "min"),
                opt(CONF_BOILER_MANUAL_HOLD_MINUTES, minutes(engine.boiler_manual_hold)): _number(5, 1440, 5, "min"),
                opt(CONF_TRV_OFFLINE_MINUTES, minutes(alerts.trv_offline_after)): _number(10, 1440, 5, "min"),
                opt(CONF_TARGET_WINDOW_HOURS, hours(alerts.target_window)): _number(1, 24, 0.5, "h"),
                opt(CONF_OUTAGE_FAILURES, alerts.outage_after_failures): _number(1, 20, 1),
                opt(CONF_SENSOR_STALE_HOURS, hours(alerts.sensor_stale_after)): _number(1, 48, 0.5, "h"),
                opt(CONF_BATTERY_LOW_PERCENT, alerts.battery_low_percent): _number(5, 50, 1, "%"),
                opt(CONF_NOTIFY_TARGETS, []): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=self._notify_services(), multiple=True, custom_value=True
                    )
                ),
                opt(CONF_NOTIFY_DELAY_MINUTES, DEFAULT_NOTIFY_DELAY_MINUTES): _number(0, 240, 5, "min"),
                opt(CONF_Z2M_BASE_TOPIC, DEFAULT_Z2M_BASE_TOPIC): selector.TextSelector(),
            }
        )
        return self.async_show_form(step_id="advanced_settings", data_schema=schema)

    def _notify_services(self) -> list[str]:
        """Notify services to push alerts to (phones and the like), as `notify.<name>`."""
        names = self.hass.services.async_services_for_domain("notify")
        skip = {"send_message", "persistent_notification"}
        return sorted(f"notify.{name}" for name in names if name not in skip)

    async def async_step_save(self, user_input=None):
        return self.async_create_entry(data={CONF_ROOMS: self.rooms, **self._settings})

    async def async_step_add_room(self, user_input=None):
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                self._rooms = add_room(self.rooms, self._room_from_input(user_input))
                return await self.async_step_init()
            except RoomError as err:
                errors["base"] = "invalid_room"
                placeholders = {"reason": self._reason(err)}
                return self.async_show_form(
                    step_id="add_room",
                    data_schema=_room_schema(user_input),
                    errors=errors,
                    description_placeholders=placeholders,
                )
        return self.async_show_form(
            step_id="add_room",
            data_schema=_room_schema(None, "living_area"),
            description_placeholders={"reason": ""},
        )

    def _room_picker(self) -> vol.Schema:
        names = [r["name"] for r in self.rooms]
        return vol.Schema(
            {
                vol.Required("room"): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=names)
                )
            }
        )

    async def async_step_edit_room(self, user_input=None):
        if user_input is not None:
            self._editing = user_input["room"]
            return await self.async_step_edit_room_details()
        return self.async_show_form(step_id="edit_room", data_schema=self._room_picker())

    async def async_step_edit_room_details(self, user_input=None):
        current = next(r for r in self.rooms if r["name"] == self._editing)
        if user_input is not None:
            try:
                assert self._editing is not None
                self._rooms = replace_room(self.rooms, self._editing, self._room_from_input(user_input))
                return await self.async_step_init()
            except RoomError as err:
                return self.async_show_form(
                    step_id="edit_room_details",
                    data_schema=_room_schema(user_input),
                    errors={"base": "invalid_room"},
                    description_placeholders={"reason": self._reason(err)},
                )
        return self.async_show_form(
            step_id="edit_room_details",
            data_schema=_room_schema(current),
            description_placeholders={"reason": ""},
        )

    async def async_step_remove_room(self, user_input=None):
        if user_input is not None:
            self._rooms = remove_room(self.rooms, user_input["room"])
            return await self.async_step_init()
        return self.async_show_form(step_id="remove_room", data_schema=self._room_picker())
