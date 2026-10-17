"""Pure mapping between stored Room config (config entry options) and the engine.

No Home Assistant imports. A stored room is a JSON-serialisable dict:
  name, trv_entity, [sensor_entity], [comfort], [setback], [frost_hold],
  [schedule: list of {days: [0..6], start: "HH:MM", end: "HH:MM"}]
"""

from __future__ import annotations

from datetime import time
from typing import Any, Mapping, Sequence

from .engine import (
    DEFAULT_COMFORT,
    DEFAULT_FROST_HOLD,
    DEFAULT_SETBACK,
    RoomConfig,
    ScheduleWindow,
)


MIN_TEMP = 5.0
MAX_TEMP = 30.0
MIN_FROST_HOLD = 5.0

DAY_NAMES = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


class RoomError(ValueError):
    """Invalid room configuration. The message is a short reason."""


def _parse_time(text: str) -> time:
    try:
        hh, mm = text.strip().split(":")
        return time(int(hh), int(mm))
    except (ValueError, TypeError) as err:
        raise RoomError(f"invalid time {text!r}") from err


def _parse_days(text: str) -> list[int]:
    text = text.strip().lower()
    if text == "daily":
        return list(range(7))
    days: set[int] = set()
    for part in text.split(","):
        part = part.strip()
        if "-" in part:
            a, _, b = part.partition("-")
            if a not in DAY_NAMES or b not in DAY_NAMES:
                raise RoomError(f"invalid days {part!r}")
            i, j = DAY_NAMES.index(a), DAY_NAMES.index(b)
            days.update(range(i, j + 1) if i <= j else [*range(i, 7), *range(0, j + 1)])
        elif part in DAY_NAMES:
            days.add(DAY_NAMES.index(part))
        else:
            raise RoomError(f"invalid days {part!r}")
    return sorted(days)


def parse_schedule(text: str) -> list[dict[str, Any]]:
    """Parse lines like 'mon,wed,fri 08:00-17:00', 'mon-fri 07:00-09:00', 'daily 06:00-23:00'."""
    windows: list[dict[str, Any]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            days_text, span = line.rsplit(None, 1)
            start_text, end_text = span.split("-")
        except ValueError as err:
            raise RoomError(f"invalid schedule line {line!r}") from err
        start, end = _parse_time(start_text), _parse_time(end_text)
        if start == end:
            raise RoomError(f"empty window in {line!r}")
        windows.append(
            {
                "days": _parse_days(days_text),
                "start": start.strftime("%H:%M"),
                "end": end.strftime("%H:%M"),
            }
        )
    return windows


def format_schedule(windows: Sequence[Mapping[str, Any]]) -> str:
    lines = []
    for w in windows:
        days = sorted(w["days"])
        days_text = "daily" if days == list(range(7)) else ",".join(DAY_NAMES[d] for d in days)
        lines.append(f"{days_text} {w['start']}-{w['end']}")
    return "\n".join(lines)


def validate_room(room: Mapping[str, Any]) -> None:
    if not str(room.get("name", "")).strip():
        raise RoomError("name is required")
    if not str(room.get("trv_entity", "")).strip():
        raise RoomError("trv entity is required")
    comfort = float(room.get("comfort", DEFAULT_COMFORT))
    setback = float(room.get("setback", DEFAULT_SETBACK))
    frost = float(room.get("frost_hold", DEFAULT_FROST_HOLD))
    if not (MIN_TEMP <= comfort <= MAX_TEMP):
        raise RoomError(f"comfort must be {MIN_TEMP}-{MAX_TEMP}")
    if frost < MIN_FROST_HOLD:
        raise RoomError(f"frost hold must be at least {MIN_FROST_HOLD}")
    if not (frost <= setback <= comfort):
        raise RoomError("need frost hold <= setback <= comfort")
    for w in room.get("schedule", ()):
        _parse_time(w["start"])
        _parse_time(w["end"])


def _check_unique(others: Sequence[Mapping[str, Any]], room: Mapping[str, Any]) -> None:
    if any(o["name"] == room["name"] for o in others):
        raise RoomError("a room with that name already exists")
    if any(o["trv_entity"] == room["trv_entity"] for o in others):
        raise RoomError("that trv entity is already used by another room")


def add_room(rooms: Sequence[Mapping[str, Any]], room: Mapping[str, Any]) -> list[dict[str, Any]]:
    validate_room(room)
    _check_unique(rooms, room)
    return [*map(dict, rooms), dict(room)]


def replace_room(
    rooms: Sequence[Mapping[str, Any]], name: str, room: Mapping[str, Any]
) -> list[dict[str, Any]]:
    if not any(r["name"] == name for r in rooms):
        raise RoomError(f"unknown room {name!r}")
    validate_room(room)
    _check_unique([r for r in rooms if r["name"] != name], room)
    return [dict(room) if r["name"] == name else dict(r) for r in rooms]


def remove_room(rooms: Sequence[Mapping[str, Any]], name: str) -> list[dict[str, Any]]:
    if not any(r["name"] == name for r in rooms):
        raise RoomError(f"unknown room {name!r}")
    return [dict(r) for r in rooms if r["name"] != name]


def to_engine_rooms(rooms: Sequence[Mapping[str, Any]]) -> tuple[RoomConfig, ...]:
    return tuple(
        RoomConfig(
            name=r["name"],
            comfort=float(r.get("comfort", DEFAULT_COMFORT)),
            setback=float(r.get("setback", DEFAULT_SETBACK)),
            frost_hold=float(r.get("frost_hold", DEFAULT_FROST_HOLD)),
            schedule=tuple(
                ScheduleWindow(
                    frozenset(w["days"]), _parse_time(w["start"]), _parse_time(w["end"])
                )
                for w in r.get("schedule", ())
            ),
        )
        for r in rooms
    )


def trv_entities(rooms: Sequence[Mapping[str, Any]]) -> dict[str, str]:
    return {r["name"]: r["trv_entity"] for r in rooms}


def sensor_entities(rooms: Sequence[Mapping[str, Any]]) -> dict[str, str]:
    return {r["name"]: r["sensor_entity"] for r in rooms if r.get("sensor_entity")}
