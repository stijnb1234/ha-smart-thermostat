"""Pure trackers of short-lived Room behaviour that feed the learned insights and alerts."""

from __future__ import annotations

from datetime import datetime, timedelta

COAST_MAX_WAIT = timedelta(minutes=60)
COAST_FALL = 0.1  # K below the peak that ends the coast observation
STALL_AFTER = timedelta(minutes=45)
STALL_RISE = 0.3  # K of warming that counts as progress


class CoastTracker:
    """After a Room stops calling for heat, how much further does it rise before it peaks."""

    def __init__(self) -> None:
        self._calling: dict[str, bool] = {}
        # room -> (stopped_at, temp when it stopped, peak so far)
        self._stopped: dict[str, tuple[datetime, float, float]] = {}

    def observe(
        self, room: str, now: datetime, temp: float | None, calling: bool, valid: bool = True
    ) -> float | None:
        """The finished coast (K) once the Room peaked, else None.

        `valid` is False while something other than the schedule steers the Room (window pause,
        boost, away), which would make the observation meaningless.
        """
        was_calling = self._calling.get(room, False)
        self._calling[room] = calling
        if temp is None or calling or not valid:
            self._stopped.pop(room, None)
            return None
        if was_calling:
            self._stopped[room] = (now, temp, temp)
            return None
        stopped = self._stopped.get(room)
        if stopped is None:
            return None
        at, start, peak = stopped
        peak = max(peak, temp)
        if temp < peak - COAST_FALL or now - at >= COAST_MAX_WAIT:
            del self._stopped[room]
            return peak - start
        self._stopped[room] = (at, start, peak)
        return None


class StallTracker:
    """Rooms that keep calling for heat but do not get warmer."""

    def __init__(self) -> None:
        self._since: dict[str, tuple[datetime, float]] = {}

    def observe(self, room: str, now: datetime, temp: float | None, calling: bool) -> None:
        if temp is None or not calling:
            self._since.pop(room, None)
            return
        started = self._since.get(room)
        if started is None or temp >= started[1] + STALL_RISE:
            self._since[room] = (now, temp)

    def stalled(self, now: datetime) -> frozenset[str]:
        return frozenset(r for r, (at, _) in self._since.items() if now - at >= STALL_AFTER)


# Long enough for the remaining fall to stay below the lowest learned window threshold (0.5 K).
RADIATOR_COOLDOWN = timedelta(minutes=60)


class RadiatorCooldown:
    """Rooms whose radiator was hot until recently and is now cooling down.

    A radiator is hot while the boiler runs and its Room is below target (the valve is open).
    For `RADIATOR_COOLDOWN` after that ends the TRV's own sensor, mounted on the valve, keeps
    falling although the Room does not cool: open-window detection must not trust it then.
    """

    def __init__(self) -> None:
        self._hot: dict[str, bool] = {}
        self._cooling_since: dict[str, datetime] = {}

    def observe(self, room: str, now: datetime, hot: bool) -> None:
        if hot:
            self._cooling_since.pop(room, None)
        elif self._hot.get(room, False):
            self._cooling_since[room] = now
        self._hot[room] = hot

    def cooling(self, now: datetime) -> frozenset[str]:
        return frozenset(r for r, since in self._cooling_since.items() if now - since < RADIATOR_COOLDOWN)
