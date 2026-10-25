"""Thin presence adapter over HA person entities.

Reports whether anyone is home or heading home. Heading home is detected automatically from
the GPS position of tracked people (arrival.py), so no "near home" zone is needed; optional
heading-home entities (a zone, a switch, a person in a zone) still work on top of that.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from .arrival import MAX_ACCURACY_M, ArrivalDetector, distance_km

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

# A heading-home entity is active in any state but these (a person in a zone has the zone name).
_NOT_ARRIVING = ("not_home", "off", "unavailable", "unknown")
_GPS_DOMAINS = ("person", "device_tracker")


def is_arriving(entity_id: str, state: str | None) -> bool:
    """A zone counts the people in it, so it is active above zero; other entities in any active state."""
    if state is None or state in _NOT_ARRIVING:
        return False
    if entity_id.startswith("zone."):
        try:
            return int(state) > 0
        except ValueError:
            return False
    return True


class PresenceAdapter:
    def __init__(
        self,
        hass: HomeAssistant,
        persons: Iterable[str],
        arrival: Iterable[str] = (),
        auto_arrival: bool = True,
        also_track: Iterable[str] = (),
    ) -> None:
        """persons are person entity ids; `also_track` adds Room occupants for arrival detection."""
        self._hass = hass
        self._persons = tuple(persons)
        self._arrival = tuple(arrival)
        self._auto = auto_arrival
        self._tracked = tuple(
            dict.fromkeys(e for e in (*self._persons, *also_track) if e.split(".", 1)[0] in _GPS_DOMAINS)
        )
        self._detector = ArrivalDetector()

    def update(self, horizon: timedelta) -> None:
        """Feed the latest GPS fixes; `horizon` is how long the house needs to warm up."""
        if not self._auto:
            return
        home_lat, home_lon = self._hass.config.latitude, self._hass.config.longitude
        for entity in self._tracked:
            state = self._hass.states.get(entity)
            if state is None:
                continue
            attrs = state.attributes
            lat, lon = attrs.get("latitude"), attrs.get("longitude")
            accuracy = attrs.get("gps_accuracy") or 0
            distance = None
            if isinstance(lat, (int, float)) and isinstance(lon, (int, float)) and accuracy <= MAX_ACCURACY_M:
                distance = distance_km(home_lat, home_lon, lat, lon)
            self._detector.observe(entity, state.last_updated, distance, state.state == "home", horizon)

    def arriving_people(self, now: datetime) -> frozenset[str]:
        """Tracked people (person/device_tracker ids) heading home right now, by GPS."""
        return frozenset(e for e in self._tracked if self._detector.arriving(e, now))

    def anyone_home(self, now: datetime) -> bool:
        """True if a tracked person is home or heading home; with none tracked, assume home."""
        if not self._persons:
            return True
        if self.arriving(now):
            return True
        return any(
            (state := self._hass.states.get(p)) is not None and state.state == "home"
            for p in self._persons
        )

    def arriving(self, now: datetime) -> bool:
        """Someone is heading home: by GPS, or a heading-home entity is active."""
        if any(p in self.arriving_people(now) for p in self._persons):
            return True
        return any(
            is_arriving(e, state.state if (state := self._hass.states.get(e)) else None)
            for e in self._arrival
        )

    def eta(self, now: datetime) -> timedelta | None:
        """Soonest estimated arrival of a tracked person heading home, for the status."""
        etas = [eta for p in self._persons if (eta := self._detector.eta(p, now)) is not None]
        return min(etas) if etas else None
