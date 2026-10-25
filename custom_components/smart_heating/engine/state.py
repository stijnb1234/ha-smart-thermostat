"""Serialise the engine's Commands so manual-change and write bookkeeping survives restarts."""

from __future__ import annotations

from collections.abc import Collection, Mapping
from datetime import datetime
from typing import Any

from .models import Commands

SCHEMA_VERSION = 2
# Version 1 named the boiler fields after the Bosch EasyControl.
_V1_NAMES = {
    "easycontrol_setpoint": "boiler_setpoint",
    "easycontrol_changed_at": "boiler_changed_at",
    "easycontrol_hold_until": "boiler_hold_until",
}
# Sections keyed by Room (stored by Room id, see rooms.RoomKeys).
PER_ROOM_KEYS = ("trv_setpoints", "trv_written_at", "trv_previous", "trv_retries", "trv_manual")


def _times(values: Mapping[str, datetime]) -> dict[str, str]:
    return {k: v.isoformat() for k, v in values.items()}


def _when(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def commands_to_dict(c: Commands, away_since: datetime | None = None) -> dict[str, Any]:
    """Commands plus when the house became empty (kept here: both are cross-cycle state)."""
    return {
        "version": SCHEMA_VERSION,
        "trv_setpoints": dict(c.trv_setpoints),
        "trv_written_at": _times(c.trv_written_at),
        "trv_previous": dict(c.trv_previous),
        "trv_retries": dict(c.trv_retries),
        "trv_manual": dict(c.trv_manual),
        "boiler_setpoint": c.boiler_setpoint,
        "boiler_changed_at": _when(c.boiler_changed_at),
        "boiler_hold_until": _when(c.boiler_hold_until),
        "away_since": _when(away_since),
    }


def _parse_time(value: Any) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def commands_from_dict(data: Mapping[str, Any] | None, rooms: Collection[str]) -> Commands:
    """Restore Commands; unknown versions, bad data and Rooms no longer configured are dropped."""
    if not data or data.get("version") not in (1, SCHEMA_VERSION):
        return Commands()
    if data.get("version") == 1:
        data = {_V1_NAMES.get(k, k): v for k, v in data.items()}
    keep = set(rooms)

    def per_room(key: str, cast) -> dict[str, Any]:
        return {k: cast(v) for k, v in (data.get(key) or {}).items() if k in keep}

    try:
        setpoint = data.get("boiler_setpoint")
        return Commands(
            trv_setpoints=per_room("trv_setpoints", float),
            trv_written_at=per_room("trv_written_at", datetime.fromisoformat),
            trv_previous=per_room("trv_previous", float),
            trv_retries=per_room("trv_retries", int),
            trv_manual=per_room("trv_manual", float),
            boiler_setpoint=None if setpoint is None else float(setpoint),
            boiler_changed_at=_parse_time(data.get("boiler_changed_at")),
            boiler_hold_until=_parse_time(data.get("boiler_hold_until")),
        )
    except (TypeError, ValueError, AttributeError):
        return Commands()


def away_since_from_dict(data: Mapping[str, Any] | None) -> datetime | None:
    try:
        return _parse_time((data or {}).get("away_since"))
    except (TypeError, ValueError):
        return None
