"""Pure mapping between stored Room config (config entry options) and the engine.

No Home Assistant imports. A stored room is a JSON-serialisable dict:
  id (stable: set once from the name, kept on rename; keys entities and learned data),
  name, [trv_entity], [manual], [floor_heating: no TRV, needs sensor; long pre-heat], [open_radiators: no TRV yet, needs sensor; caps the boiler call at its comfort], [sensor_entity], [arrival_entities: same kinds, or a person in a zone; active = heading home, room warms early],
  [presence_entities: person/tracker/switch ids; room is skipped by the
  schedule while all are away], [comfort], [setback], [frost_hold],
  [trv_offset], [lead_time_minutes], [window_detection], [window_drop],
  [window_pause_minutes],
  [schedule: list of {days: [0..6], start: "HH:MM", end: "HH:MM"}]
A `manual` Room has no Zigbee TRV (floor heating, dumb TRV): the engine does not
control it; it only matters through the Manual-room override.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable, Collection, Mapping, Sequence
from datetime import time, timedelta
from typing import Any

from .engine import (
    DEFAULT_COMFORT,
    DEFAULT_FLOOR_LEAD_TIME,
    DEFAULT_FROST_HOLD,
    DEFAULT_LEAD_TIME,
    DEFAULT_LIVING_AREA_SCHEDULE,
    DEFAULT_SETBACK,
    DEFAULT_WORK_SCHEDULE,
    RoomConfig,
    ScheduleWindow,
)
from .i18n import tr

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
# Dutch day names are accepted too (schedule text is typed by the user).
DAY_ALIASES = {"ma": "mon", "di": "tue", "wo": "wed", "do": "thu", "vr": "fri", "za": "sat", "zo": "sun"}


class RoomError(ValueError):
    """Invalid room configuration. `code` and `params` identify the reason for translation;
    the message is the English reason."""

    def __init__(self, code: str, **params: Any) -> None:
        self.code, self.params = code, params
        super().__init__(tr("en", f"room_error.{code}", **params))


def slug(text: str) -> str:
    """Lowercase ASCII words joined by underscores, as in Home Assistant object ids."""
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", ascii_text.lower()).strip("_")


def _parse_time(text: str) -> time:
    try:
        hh, mm, *_seconds = text.strip().split(":")  # HH:MM or HH:MM:SS (time selector)
        return time(int(hh), int(mm))
    except (ValueError, TypeError) as err:
        raise RoomError("invalid_time", text=repr(text)) from err


def _parse_days(text: str) -> list[int]:
    text = text.strip().lower()
    if text in ("daily", "dagelijks"):
        return list(range(7))
    days: set[int] = set()
    for part in text.split(","):
        part = part.strip()
        if "-" in part:
            a, _, b = part.partition("-")
            a, b = DAY_ALIASES.get(a.strip(), a.strip()), DAY_ALIASES.get(b.strip(), b.strip())
            if a not in DAY_NAMES or b not in DAY_NAMES:
                raise RoomError("invalid_days", text=repr(part))
            i, j = DAY_NAMES.index(a), DAY_NAMES.index(b)
            days.update(range(i, j + 1) if i <= j else [*range(i, 7), *range(j + 1)])
        elif DAY_ALIASES.get(part, part) in DAY_NAMES:
            days.add(DAY_NAMES.index(DAY_ALIASES.get(part, part)))
        else:
            raise RoomError("invalid_days", text=repr(part))
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
            raise RoomError("invalid_line", text=repr(line)) from err
        start, end = _parse_time(start_text), _parse_time(end_text)
        if start == end:
            raise RoomError("empty_window", text=repr(line))
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
    if room.get("floor_heating") or room.get("open_radiators"):
        room.pop("manual", None)  # a sensor-only room is controlled: not a manual room
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
        raise RoomError("name_required")
    if not slug(str(room["name"])):
        raise RoomError("name_needs_letters")
    if room.get("floor_heating") or room.get("open_radiators"):
        if not str(room.get("sensor_entity", "")).strip():
            raise RoomError("floor_needs_sensor")
    elif not room.get("manual") and not str(room.get("trv_entity", "")).strip():
        raise RoomError("trv_required")
    comfort = float(room.get("comfort", DEFAULT_COMFORT))
    setback = float(room.get("setback", DEFAULT_SETBACK))
    frost = float(room.get("frost_hold", DEFAULT_FROST_HOLD))
    if not (MIN_TEMP <= comfort <= MAX_TEMP):
        raise RoomError("comfort_range", low=MIN_TEMP, high=MAX_TEMP)
    if frost < MIN_FROST_HOLD:
        raise RoomError("frost_min", low=MIN_FROST_HOLD)
    if not (frost <= setback <= comfort):
        raise RoomError("temp_order")
    for w in room.get("schedule", ()):
        _parse_time(w["start"])
        _parse_time(w["end"])
    for key, low, high in NUMERIC_LIMITS:
        if key in room and not (low <= float(room[key]) <= high):
            raise RoomError("out_of_range", key=key, low=low, high=high)


def _check_unique(others: Sequence[Mapping[str, Any]], room: Mapping[str, Any]) -> None:
    # Names that only differ in case or punctuation would give the same entity ids.
    if any(slug(o["name"]) == slug(room["name"]) for o in others):
        raise RoomError("duplicate_name")
    trv = room.get("trv_entity")
    if trv and any(o.get("trv_entity") == trv for o in others):
        raise RoomError("duplicate_trv")


def _free_id(name: str, taken: Collection[str]) -> str:
    base = slug(name)
    candidate, n = base, 1
    while candidate in taken:
        n += 1
        candidate = f"{base}_{n}"
    return candidate


def add_room(rooms: Sequence[Mapping[str, Any]], room: Mapping[str, Any]) -> list[dict[str, Any]]:
    validate_room(room)
    _check_unique(rooms, room)
    new = {**room, "id": _free_id(room["name"], {r["id"] for r in rooms if r.get("id")})}
    return [*map(dict, rooms), new]


def replace_room(
    rooms: Sequence[Mapping[str, Any]], name: str, room: Mapping[str, Any]
) -> list[dict[str, Any]]:
    current = next((r for r in rooms if r["name"] == name), None)
    if current is None:
        raise RoomError("unknown_room", text=repr(name))
    validate_room(room)
    _check_unique([r for r in rooms if r["name"] != name], room)
    edited = {**room, "id": current.get("id") or _free_id(name, {r["id"] for r in rooms if r.get("id")})}
    return [edited if r["name"] == name else dict(r) for r in rooms]


def ensure_room_ids(rooms: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Give Rooms stored before ids existed an id from their name (their entity ids so far)."""
    taken = {r["id"] for r in rooms if r.get("id")}
    result = []
    for r in rooms:
        if not r.get("id"):
            r = {**r, "id": _free_id(r["name"], taken)}
            taken.add(r["id"])
        result.append(dict(r))
    return result


def room_id(room: Mapping[str, Any]) -> str:
    return room.get("id") or slug(room["name"])


class RoomKeys:
    """Translates Room keys between the engine (names, readable in alerts and logs) and
    storage (ids, so learned data and bookkeeping survive a rename)."""

    def __init__(self, rooms: Sequence[Mapping[str, Any]]) -> None:
        self._id_of = {r["name"]: room_id(r) for r in rooms}
        self._name_of = {room_id(r): r["name"] for r in rooms}

    def to_ids(self, by_name: Mapping[str, Any]) -> dict[str, Any]:
        return {self._id_of[n]: v for n, v in by_name.items() if n in self._id_of}

    def to_names(self, stored: Mapping[str, Any]) -> dict[str, Any]:
        """Stored keys are ids; data saved by name before ids existed is read too."""
        result: dict[str, Any] = {}
        for key, value in stored.items():
            name = self._name_of.get(key) or (key if key in self._id_of else None)
            if name is not None:
                result.setdefault(name, value)
        return result

    def _sections(
        self, data: Mapping[str, Any] | None, sections: Sequence[str], convert: Callable
    ) -> dict[str, Any] | None:
        if data is None:
            return None
        return {
            k: convert(v) if k in sections and isinstance(v, Mapping) else v for k, v in data.items()
        }

    def sections_to_ids(self, data: Mapping[str, Any], sections: Sequence[str]) -> dict[str, Any]:
        """`data` with the per-Room mappings under `sections` keyed by id."""
        return self._sections(data, sections, self.to_ids) or {}

    def sections_to_names(
        self, data: Mapping[str, Any] | None, sections: Sequence[str]
    ) -> dict[str, Any] | None:
        return self._sections(data, sections, self.to_names)


def remove_room(rooms: Sequence[Mapping[str, Any]], name: str) -> list[dict[str, Any]]:
    if not any(r["name"] == name for r in rooms):
        raise RoomError("unknown_room", text=repr(name))
    return [dict(r) for r in rooms if r["name"] != name]


def to_engine_rooms(rooms: Sequence[Mapping[str, Any]]) -> tuple[RoomConfig, ...]:
    """Engine Rooms; `manual` Rooms (no TRV) are not controlled and so are left out."""
    defaults = RoomConfig(name="")
    return tuple(
        RoomConfig(
            name=r["name"],
            id=room_id(r),
            comfort=float(r.get("comfort", DEFAULT_COMFORT)),
            setback=float(r.get("setback", DEFAULT_SETBACK)),
            frost_hold=float(r.get("frost_hold", DEFAULT_FROST_HOLD)),
            trv_offset=float(r.get("trv_offset", defaults.trv_offset)),
            floor_heating=bool(r.get("floor_heating")),
            open_radiators=bool(r.get("open_radiators")),
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
        if not is_manual(r)
    )


def is_manual(room: Mapping[str, Any]) -> bool:
    """A manual room is not controlled by the engine. Floor heating and open radiators win over the manual flag."""
    return bool(room.get("manual")) and not (room.get("floor_heating") or room.get("open_radiators"))


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
