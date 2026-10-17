"""Pure detector of completed warm-ups, feeding the lead-time learner. No HA imports."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

MIN_DELTA = 1.0  # ignore tiny rises, too noisy to give a heating rate
DONE_MARGIN = 0.2
MAX_DURATION = timedelta(hours=6)


@dataclass(frozen=True)
class Warmup:
    room: str
    outdoor_temp: float
    delta: float
    duration: timedelta


class WarmupTracker:
    """A warm-up runs while a Room's target is comfort and it is still below it."""

    def __init__(self) -> None:
        self._active: dict[str, tuple[datetime, float, float]] = {}

    def observe(
        self,
        room: str,
        now: datetime,
        temp: float | None,
        target: float,
        comfort: float,
        outdoor_temp: float | None,
    ) -> Warmup | None:
        active = self._active.get(room)
        if temp is None or target != comfort or outdoor_temp is None:
            self._active.pop(room, None)
            return None
        if active is None:
            if comfort - temp >= MIN_DELTA:
                self._active[room] = (now, temp, outdoor_temp)
            return None
        started, start_temp, outdoor = active
        if now - started > MAX_DURATION:
            del self._active[room]
            return None
        if temp >= comfort - DONE_MARGIN:
            del self._active[room]
            return Warmup(room, outdoor, comfort - start_temp, now - started)
        return None
