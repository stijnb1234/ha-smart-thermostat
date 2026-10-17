"""Thin presence adapter over HA person entities.

Reports whether anyone is home and since when everyone has been away, for the
engine's `anyone_home` and `away_since` inputs.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Iterable

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

# A heading-home entity is active in any state but these (a person in a zone has the zone name).
_NOT_ARRIVING = ("not_home", "off", "unavailable", "unknown")


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
        self, hass: HomeAssistant, persons: Iterable[str], arrival: Iterable[str] = ()
    ) -> None:
        """persons are person entity ids, e.g. person.stijn."""
        self._hass = hass
        self._persons = tuple(persons)
        self._arrival = tuple(arrival)

    def anyone_home(self) -> bool:
        """True if a tracked person is home or heading home; with none tracked, assume home."""
        if not self._persons:
            return True
        if self.arriving():
            return True
        return any(
            (state := self._hass.states.get(p)) is not None and state.state == "home"
            for p in self._persons
        )

    def arriving(self) -> bool:
        """A heading-home entity is active: on, a zone with someone in it, or a person in any zone."""
        return any(
            is_arriving(e, state.state if (state := self._hass.states.get(e)) else None)
            for e in self._arrival
        )

    def away_since(self) -> datetime | None:
        """When the last tracked person left, or None while someone is home."""
        if self.anyone_home():
            return None
        changed = [
            state.last_changed
            for p in self._persons
            if (state := self._hass.states.get(p)) is not None
        ]
        return max(changed) if changed else None
