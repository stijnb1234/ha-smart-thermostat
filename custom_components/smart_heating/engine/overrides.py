"""Boost (per Room) and Manual-room override: timed requests that expire on their own."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Mapping


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
