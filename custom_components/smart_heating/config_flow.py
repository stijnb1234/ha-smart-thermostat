"""Thin HA glue: config flow creates the entry, options flow edits Rooms.

All validation and mapping lives in rooms.py (pure, unit-tested).
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import CONF_GAS_ENTITY, CONF_HDD_BASE, CONF_OUTDOOR_ENTITY, CONF_ROOMS, DOMAIN
from .report import DEFAULT_HDD_BASE

REPORT_KEYS = (CONF_GAS_ENTITY, CONF_OUTDOOR_ENTITY, CONF_HDD_BASE)
from .rooms import (
    DEFAULT_COMFORT,
    DEFAULT_FROST_HOLD,
    DEFAULT_SETBACK,
    RoomError,
    add_room,
    format_schedule,
    parse_schedule,
    remove_room,
    replace_room,
)


class SmartHeatingConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

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


def _room_schema(room: dict[str, Any] | None) -> vol.Schema:
    room = room or {}

    def opt(key, default=None):
        value = room.get(key, default)
        return vol.Optional(key, description={"suggested_value": value})

    comfort, _ = _temp(DEFAULT_COMFORT)
    return vol.Schema(
        {
            vol.Required("name", description={"suggested_value": room.get("name")}): str,
            vol.Required(
                "trv_entity", description={"suggested_value": room.get("trv_entity")}
            ): selector.EntitySelector(selector.EntitySelectorConfig(domain="climate")),
            opt("sensor_entity"): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="temperature")
            ),
            opt("comfort", DEFAULT_COMFORT): comfort,
            opt("setback", DEFAULT_SETBACK): comfort,
            opt("frost_hold", DEFAULT_FROST_HOLD): comfort,
            opt("schedule_text", format_schedule(room.get("schedule", []))): selector.TextSelector(
                selector.TextSelectorConfig(multiline=True)
            ),
        }
    )


def _room_from_input(user_input: dict[str, Any]) -> dict[str, Any]:
    room = {k: v for k, v in user_input.items() if k != "schedule_text" and v not in (None, "")}
    room["schedule"] = parse_schedule(user_input.get("schedule_text") or "")
    return room


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
            self._settings_cache = {k: opts[k] for k in REPORT_KEYS if k in opts}
        return self._settings_cache

    @_settings.setter
    def _settings(self, value: dict[str, Any]) -> None:
        self._settings_cache = value

    @property
    def rooms(self) -> list[dict[str, Any]]:
        if self._rooms is None:
            self._rooms = [dict(r) for r in self.config_entry.options.get(CONF_ROOMS, [])]
        return self._rooms

    async def async_step_init(self, user_input=None):
        options = ["add_room"]
        if self.rooms:
            options += ["edit_room", "remove_room"]
        options += ["report_settings", "save"]
        return self.async_show_menu(step_id="init", menu_options=options)

    async def async_step_report_settings(self, user_input=None):
        current = self._settings
        if user_input is not None:
            self._settings = {k: v for k, v in user_input.items() if v not in (None, "")}
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

    async def async_step_save(self, user_input=None):
        return self.async_create_entry(data={CONF_ROOMS: self.rooms, **self._settings})

    async def async_step_add_room(self, user_input=None):
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                self._rooms = add_room(self.rooms, _room_from_input(user_input))
                return await self.async_step_init()
            except RoomError as err:
                errors["base"] = "invalid_room"
                placeholders = {"reason": str(err)}
                return self.async_show_form(
                    step_id="add_room",
                    data_schema=_room_schema(user_input),
                    errors=errors,
                    description_placeholders=placeholders,
                )
        return self.async_show_form(
            step_id="add_room",
            data_schema=_room_schema(None),
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
                self._rooms = replace_room(self.rooms, self._editing, _room_from_input(user_input))
                return await self.async_step_init()
            except RoomError as err:
                return self.async_show_form(
                    step_id="edit_room_details",
                    data_schema=_room_schema(user_input),
                    errors={"base": "invalid_room"},
                    description_placeholders={"reason": str(err)},
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
