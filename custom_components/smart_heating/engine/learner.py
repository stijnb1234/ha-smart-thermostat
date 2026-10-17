"""Pure learner of per-Room pre-heat lead time. No Home Assistant imports.

Each observed warm-up yields a heating rate (K/h) at a given outdoor
temperature. Per Room we fit rate = a + b * outdoor (least squares) over the
most recent samples; lead time = temperature delta / rate.
"""

from __future__ import annotations

from collections import deque
from datetime import timedelta
from typing import Any, Mapping

SCHEMA_VERSION = 2
MIN_SAMPLES = 5
MAX_SAMPLES = 50
MIN_LEAD_TIME = timedelta(minutes=10)
MAX_LEAD_TIME = timedelta(hours=4)
_MIN_RATE = 1e-6


class LeadTimeLearner:
    def __init__(self) -> None:
        # room -> deque of (outdoor_temp, rate_k_per_h)
        self._samples: dict[str, deque[tuple[float, float]]] = {}

    def record_warmup(
        self, room: str, outdoor_temp: float, delta: float, duration: timedelta
    ) -> None:
        """Record a completed warm-up that raised `room` by `delta` K in `duration`."""
        hours = duration.total_seconds() / 3600
        if delta <= 0 or hours <= 0:
            return
        samples = self._samples.setdefault(room, deque(maxlen=MAX_SAMPLES))
        samples.append((outdoor_temp, delta / hours))

    def estimate(
        self, room: str, outdoor_temp: float, delta: float
    ) -> timedelta | None:
        """Learned lead time, or None while there is too little data."""
        samples = self._samples.get(room)
        if not samples or len(samples) < MIN_SAMPLES or delta <= 0:
            return None
        rate = max(_predict_rate(samples, outdoor_temp), _MIN_RATE)
        lead = timedelta(hours=delta / rate)
        return min(max(lead, MIN_LEAD_TIME), MAX_LEAD_TIME)

    def lead_times(
        self, outdoor_temp: float, deltas: Mapping[str, float]
    ) -> dict[str, timedelta]:
        """Value for EngineInput.learned: only rooms with a usable estimate."""
        result: dict[str, timedelta] = {}
        for room, delta in deltas.items():
            lead = self.estimate(room, outdoor_temp, delta)
            if lead is not None:
                result[room] = lead
        return result

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": SCHEMA_VERSION,
            "rooms": {
                room: [{"outdoor": o, "rate": r} for o, r in samples]
                for room, samples in self._samples.items()
            },
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any] | None) -> LeadTimeLearner:
        learner = cls()
        if not data:
            return learner
        version = data.get("version")
        rooms = data.get("rooms", {})
        try:
            if version == 1:
                pairs = {
                    room: [(float(o), float(r)) for o, r in items]
                    for room, items in rooms.items()
                }
            elif version == SCHEMA_VERSION:
                pairs = {
                    room: [(float(i["outdoor"]), float(i["rate"])) for i in items]
                    for room, items in rooms.items()
                }
            else:
                return learner
        except (TypeError, ValueError, KeyError):
            return learner
        for room, items in pairs.items():
            learner._samples[room] = deque(items, maxlen=MAX_SAMPLES)
        return learner


def _predict_rate(samples: deque[tuple[float, float]], outdoor: float) -> float:
    n = len(samples)
    mean_x = sum(x for x, _ in samples) / n
    mean_y = sum(y for _, y in samples) / n
    sxx = sum((x - mean_x) ** 2 for x, _ in samples)
    if sxx < 1e-9:
        return mean_y
    slope = sum((x - mean_x) * (y - mean_y) for x, y in samples) / sxx
    return mean_y + slope * (outdoor - mean_x)
