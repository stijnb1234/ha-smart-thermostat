"""Pure heading-home detection from the GPS position of tracked people. No HA imports.

No zones to draw: a person counts as arriving when their distance to home has been shrinking
at travel speed and, at that speed, they will be home within the horizon (the time the house
needs to warm up). It stays set while they keep coming closer, and ends when they are home,
turn away or stop reporting progress.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta

EARTH_RADIUS_KM = 6371.0
SAMPLE_KEEP = timedelta(minutes=30)
MIN_SPAN = timedelta(minutes=2)  # fixes closer together than this say nothing about speed
MIN_APPROACH_KM = 0.5  # GPS jitter stays well below this
MIN_SPEED_KMH = 4.0  # walking pace or faster
TURN_AWAY_KM = 1.0  # further than the closest point since arriving: no longer heading home
MIN_HOLD = timedelta(minutes=20)  # arriving holds this long (or twice the ETA) without new progress
MAX_ACCURACY_M = 500.0  # coarser fixes (cell towers) are ignored


def distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance (haversine)."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


@dataclass
class _Arriving:
    until: datetime
    closest_km: float
    eta: timedelta


class ArrivalDetector:
    def __init__(self) -> None:
        self._fixes: dict[str, deque[tuple[datetime, float]]] = {}
        self._arriving: dict[str, _Arriving] = {}

    def observe(
        self,
        person: str,
        at: datetime,
        distance: float | None,
        home: bool,
        horizon: timedelta,
    ) -> None:
        """Feed a GPS fix taken at `at` (`distance` km from home; None when there is no usable fix)."""
        if home:
            self._fixes.pop(person, None)
            self._arriving.pop(person, None)
            return
        if distance is None:
            return
        fixes = self._fixes.setdefault(person, deque())
        if fixes and fixes[-1][0] >= at:
            return  # the same fix again (the coordinator polls faster than phones report)
        fixes.append((at, distance))
        while fixes and at - fixes[0][0] > SAMPLE_KEEP:
            fixes.popleft()

        arriving = self._arriving.get(person)
        if arriving is not None and distance > arriving.closest_km + TURN_AWAY_KM:
            del self._arriving[person]
            arriving = None
        if arriving is not None:
            arriving.closest_km = min(arriving.closest_km, distance)

        eta = self._eta(fixes)
        if eta is not None and eta <= horizon:
            hold = max(MIN_HOLD, 2 * eta)
            closest = min(distance, arriving.closest_km) if arriving else distance
            self._arriving[person] = _Arriving(at + hold, closest, eta)

    @staticmethod
    def _eta(fixes: deque[tuple[datetime, float]]) -> timedelta | None:
        """Time to home at the speed of approach over the recent fixes, None when not approaching."""
        at, distance = fixes[-1]
        for then, before in fixes:
            span = at - then
            if span < MIN_SPAN:
                break
            approach = before - distance
            speed = approach / (span.total_seconds() / 3600)
            if approach >= MIN_APPROACH_KM and speed >= MIN_SPEED_KMH:
                return timedelta(hours=distance / speed)
        return None

    def arriving(self, person: str, now: datetime) -> bool:
        state = self._arriving.get(person)
        if state is None:
            return False
        if now > state.until:
            del self._arriving[person]
            return False
        return True

    def eta(self, person: str, now: datetime) -> timedelta | None:
        """Estimated time to home when the person counts as arriving."""
        return self._arriving[person].eta if self.arriving(person, now) else None
