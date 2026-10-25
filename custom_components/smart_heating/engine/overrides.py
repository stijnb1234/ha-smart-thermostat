"""Boost (per Room) and Manual-room override: timed requests that expire on their own."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any


@dataclass(frozen=True)
class _Timed:
    start: datetime
    duration: timedelta

    def active(self, now: datetime) -> bool:
        return self.start <= now < self.start + self.duration


@dataclass(frozen=True)
class Boost(_Timed):
    """Heat a Room to comfort now, for `duration`."""


@dataclass(frozen=True)
class ManualRoomOverride(_Timed):
    """Boiler call for a dumb-TRV room the engine does not control; counts as demand."""


def boosted_rooms(boosts: Mapping[str, Boost], now: datetime) -> frozenset[str]:
    return frozenset(name for name, b in boosts.items() if b.active(now))


def manual_override_active(
    overrides: Mapping[str, ManualRoomOverride], now: datetime
) -> bool:
    return any(o.active(now) for o in overrides.values())


def timed_requests_to_dict(
    boosts: Mapping[str, Boost], overrides: Mapping[str, ManualRoomOverride]
) -> dict[str, Any]:
    """JSON-serialisable form of the active timed requests, for persistence."""

    def one(item: _Timed) -> dict[str, Any]:
        return {"start": item.start.isoformat(), "seconds": item.duration.total_seconds()}

    return {
        "boosts": {room: one(b) for room, b in boosts.items()},
        "manual_overrides": {key: one(o) for key, o in overrides.items()},
    }


def timed_requests_from_dict(
    data: Mapping[str, Any] | None, now: datetime
) -> tuple[dict[str, Boost], dict[str, ManualRoomOverride]]:
    """Inverse of `timed_requests_to_dict`. Expired or malformed entries are dropped."""
    boosts: dict[str, Boost] = {}
    overrides: dict[str, ManualRoomOverride] = {}
    data = data or {}

    def load(raw: Any, cls: type, into: dict) -> None:
        if not isinstance(raw, Mapping):
            return
        for key, item in raw.items():
            try:
                value = cls(
                    datetime.fromisoformat(item["start"]), timedelta(seconds=float(item["seconds"]))
                )
            except (KeyError, TypeError, ValueError):
                continue
            if value.start.tzinfo is not None and value.active(now):
                into[key] = value

    load(data.get("boosts") or {}, Boost, boosts)
    load(data.get("manual_overrides") or {}, ManualRoomOverride, overrides)
    return boosts, overrides
