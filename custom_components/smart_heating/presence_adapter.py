"""Thin presence adapter over HA person entities.

Reports whether anyone is home and since when everyone has been away, for the
engine's `anyone_home` and `away_since` inputs.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Iterable

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


class PresenceAdapter:
    def __init__(self, hass: HomeAssistant, persons: Iterable[str]) -> None:
        """persons are person entity ids, e.g. person.stijn."""
        self._hass = hass
        self._persons = tuple(persons)

    def anyone_home(self) -> bool:
        """True if a tracked person is home; with none tracked, assume home."""
        if not self._persons:
            return True
        return any(
            (state := self._hass.states.get(p)) is not None and state.state == "home"
            for p in self._persons
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
