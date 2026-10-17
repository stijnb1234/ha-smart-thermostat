"""Serialise the engine's Commands so manual-change and write bookkeeping survives restarts."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Collection, Mapping

from .models import Commands

SCHEMA_VERSION = 1


def _times(values: Mapping[str, datetime]) -> dict[str, str]:
    return {k: v.isoformat() for k, v in values.items()}


def commands_to_dict(c: Commands) -> dict[str, Any]:
    return {
        "version": SCHEMA_VERSION,
        "trv_setpoints": dict(c.trv_setpoints),
        "trv_written_at": _times(c.trv_written_at),
        "trv_previous": dict(c.trv_previous),
        "trv_retries": dict(c.trv_retries),
        "trv_manual": dict(c.trv_manual),
        "easycontrol_setpoint": c.easycontrol_setpoint,
        "easycontrol_changed_at": c.easycontrol_changed_at.isoformat()
        if c.easycontrol_changed_at
        else None,
        "easycontrol_hold_until": c.easycontrol_hold_until.isoformat()
        if c.easycontrol_hold_until
        else None,
    }


def commands_from_dict(data: Mapping[str, Any] | None, rooms: Collection[str]) -> Commands:
    """Restore Commands; unknown versions, bad data and Rooms no longer configured are dropped."""
    if not data or data.get("version") != SCHEMA_VERSION:
        return Commands()
    keep = set(rooms)

    def per_room(key: str, cast) -> dict[str, Any]:
        return {k: cast(v) for k, v in (data.get(key) or {}).items() if k in keep}

    def when(value: str | None) -> datetime | None:
        return datetime.fromisoformat(value) if value else None

    try:
        setpoint = data.get("easycontrol_setpoint")
        return Commands(
            trv_setpoints=per_room("trv_setpoints", float),
            trv_written_at=per_room("trv_written_at", datetime.fromisoformat),
            trv_previous=per_room("trv_previous", float),
            trv_retries=per_room("trv_retries", int),
            trv_manual=per_room("trv_manual", float),
            easycontrol_setpoint=None if setpoint is None else float(setpoint),
            easycontrol_changed_at=when(data.get("easycontrol_changed_at")),
            easycontrol_hold_until=when(data.get("easycontrol_hold_until")),
        )
    except (TypeError, ValueError):
        return Commands()
