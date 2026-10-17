"""Pure mapping between stored Room config (config entry options) and the engine.

No Home Assistant imports. A stored room is a JSON-serialisable dict:
  name, [trv_entity], [manual], [floor_heating: no TRV, needs sensor; long pre-heat], [sensor_entity], [arrival_entities: same kinds, or a person in a zone; active = heading home, room warms early],
  [presence_entities: person/tracker/switch ids; room is skipped by the
  schedule while all are away], [comfort], [setback], [frost_hold],
  [trv_offset], [lead_time_minutes], [window_detection], [window_drop],
  [window_pause_minutes],
  [schedule: list of {days: [0..6], start: "HH:MM", end: "HH:MM"}]
A `manual` Room has no Zigbee TRV (floor heating, dumb TRV): the engine does not
control it; it only matters through the Manual-room override.
"""

from __future__ import annotations

from datetime import time, timedelta
from typing import Any, Mapping, Sequence

from .engine import (
    DEFAULT_FLOOR_LEAD_TIME,
    DEFAULT_LEAD_TIME,
    DEFAULT_LIVING_AREA_SCHEDULE,
    DEFAULT_WORK_SCHEDULE,
    DEFAULT_COMFORT,
    DEFAULT_FROST_HOLD,
    DEFAULT_SETBACK,
    RoomConfig,
    ScheduleWindow,
)


MIN_TEMP = 5.0
MAX_TEMP = 30.0
MIN_FROST_HOLD = 5.0

NUMERIC_LIMITS = (
    ("trv_offset", -5.0, 5.0),
    ("lead_time_minutes", 0.0, 480.0),
    ("window_drop", 0.5, 10.0),
    ("window_pause_minutes", 15.0, 30.0),
)

PRESETS = ("none", "living_area", "working_room", "bedroom")
DEFAULT_PRE_BED = ("21:30", "22:30")

DAY_NAMES = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


class RoomError(ValueError):
    """Invalid room configuration. The message is a short reason."""


def _parse_time(text: str) -> time:
    try:
        hh, mm, *_seconds = text.strip().split(":")  # HH:MM or HH:MM:SS (time selector)
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


def _window_dict(window: ScheduleWindow) -> dict[str, Any]:
    return {
        "days": sorted(window.days),
        "start": window.start.strftime("%H:%M"),
        "end": window.end.strftime("%H:%M"),
    }


def preset_schedule(
    preset: str, pre_bed: tuple[str, str] = DEFAULT_PRE_BED
) -> list[dict[str, Any]]:
    """Default comfort windows (spec): living area, working room, bedroom (work hours + pre-bed)."""
    if preset == "living_area":
        return [_window_dict(w) for w in DEFAULT_LIVING_AREA_SCHEDULE]
    if preset == "working_room":
        return [_window_dict(w) for w in DEFAULT_WORK_SCHEDULE]
    if preset == "bedroom":
        start, end = pre_bed
        pre_bed_window = {
            "days": list(range(7)),
            "start": _parse_time(start).strftime("%H:%M"),
            "end": _parse_time(end).strftime("%H:%M"),
        }
        return [*(_window_dict(w) for w in DEFAULT_WORK_SCHEDULE), pre_bed_window]
    return []


def room_from_form(
    user_input: Mapping[str, Any], pre_bed: tuple[str, str] = DEFAULT_PRE_BED
) -> dict[str, Any]:
    """Stored Room from room-form input. A blank schedule text takes the chosen preset."""
    skip = ("schedule_text", "preset")
    room = {k: v for k, v in user_input.items() if k not in skip and v not in (None, "")}
    if room.get("floor_heating") and float(room.get("lead_time_minutes", 0)) == (
        DEFAULT_LEAD_TIME.total_seconds() / 60
    ):
        del room["lead_time_minutes"]  # the form's untouched default: use the floor default instead
    text = user_input.get("schedule_text") or ""
    if text.strip():
        room["schedule"] = parse_schedule(text)
    else:
        room["schedule"] = preset_schedule(user_input.get("preset") or "none", pre_bed)
    return room


def validate_room(room: Mapping[str, Any]) -> None:
    if not str(room.get("name", "")).strip():
        raise RoomError("name is required")
    if room.get("floor_heating"):
        if not str(room.get("sensor_entity", "")).strip():
            raise RoomError("a floor heating room needs a temperature sensor")
    elif not room.get("manual") and not str(room.get("trv_entity", "")).strip():
        raise RoomError("trv entity is required (or mark the room as manual)")
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
    for key, low, high in NUMERIC_LIMITS:
        if key in room and not (low <= float(room[key]) <= high):
            raise RoomError(f"{key} must be {low}-{high}")


def _check_unique(others: Sequence[Mapping[str, Any]], room: Mapping[str, Any]) -> None:
    if any(o["name"] == room["name"] for o in others):
        raise RoomError("a room with that name already exists")
    trv = room.get("trv_entity")
    if trv and any(o.get("trv_entity") == trv for o in others):
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
    """Engine Rooms; `manual` Rooms (no TRV) are not controlled and so are left out."""
    defaults = RoomConfig(name="")
    return tuple(
        RoomConfig(
            name=r["name"],
            comfort=float(r.get("comfort", DEFAULT_COMFORT)),
            setback=float(r.get("setback", DEFAULT_SETBACK)),
            frost_hold=float(r.get("frost_hold", DEFAULT_FROST_HOLD)),
            trv_offset=float(r.get("trv_offset", defaults.trv_offset)),
            floor_heating=bool(r.get("floor_heating")),
            lead_time=timedelta(minutes=float(r["lead_time_minutes"]))
            if "lead_time_minutes" in r
            else (DEFAULT_FLOOR_LEAD_TIME if r.get("floor_heating") else defaults.lead_time),
            window_detection=bool(r.get("window_detection", defaults.window_detection)),
            window_drop=float(r.get("window_drop", defaults.window_drop)),
            window_pause=timedelta(minutes=float(r["window_pause_minutes"]))
            if "window_pause_minutes" in r
            else defaults.window_pause,
            schedule=tuple(
                ScheduleWindow(
                    frozenset(w["days"]), _parse_time(w["start"]), _parse_time(w["end"])
                )
                for w in r.get("schedule", ())
            ),
        )
        for r in rooms
        if not r.get("manual")
    )


def trv_entities(rooms: Sequence[Mapping[str, Any]]) -> dict[str, str]:
    return {r["name"]: r["trv_entity"] for r in rooms if not r.get("manual") and r.get("trv_entity")}


def presence_entities(rooms: Sequence[Mapping[str, Any]]) -> dict[str, tuple[str, ...]]:
    return {r["name"]: tuple(r["presence_entities"]) for r in rooms if r.get("presence_entities")}


def arrival_entities(rooms: Sequence[Mapping[str, Any]]) -> dict[str, tuple[str, ...]]:
    return {r["name"]: tuple(r["arrival_entities"]) for r in rooms if r.get("arrival_entities")}


def absent_rooms(
    presence: Mapping[str, Sequence[str]],
    is_present: Mapping[str, bool | None],
    arrival: Mapping[str, Sequence[str]] | None = None,
    is_arriving: Mapping[str, bool] | None = None,
) -> frozenset[str]:
    """Rooms whose occupant entities are all known to be away (unknown counts as present).

    A room whose arrival entity signals someone heading home is not absent, so it warms up early.
    """
    arrival, is_arriving = arrival or {}, is_arriving or {}
    return frozenset(
        room
        for room, entities in presence.items()
        if entities
        and all(is_present.get(e) is False for e in entities)
        and not any(is_arriving.get(e) for e in arrival.get(room, ()))
    )


def sensor_entities(rooms: Sequence[Mapping[str, Any]]) -> dict[str, str]:
    return {r["name"]: r["sensor_entity"] for r in rooms if r.get("sensor_entity")}
