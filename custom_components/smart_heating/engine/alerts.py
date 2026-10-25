"""Alerts: level-based conditions, plus a notifier that dedupes them into raise/clear events."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime

from .models import Alert, EngineInput


def thermostat_outage(inp: EngineInput) -> bool:
    w = inp.last_write
    return (
        w is not None
        and w.status != "ok"
        and w.consecutive_failures >= inp.config.alerts.outage_after_failures
    )


def compute_alerts(inp: EngineInput) -> tuple[Alert, ...]:
    """Every alert whose condition holds right now (the active set)."""
    cfg = inp.config.alerts
    alerts: list[Alert] = []
    if thermostat_outage(inp):
        alerts.append(
            Alert("boiler_outage", None, "Boiler thermostat unreachable; boiler call is throttled, TRVs keep following the schedule")
        )
    for room in inp.config.rooms:
        name = room.name
        seen = inp.trv_last_seen.get(name)
        if seen is not None and inp.now - seen > cfg.trv_offline_after:
            alerts.append(Alert("trv_offline", name, f"TRV in {name} is offline"))
        if name in inp.trv_off:
            alerts.append(Alert("trv_off", name, f"TRV in {name} is switched off and does not turn on"))
        if inp.battery_low.get(name):
            alerts.append(Alert("low_battery", name, f"TRV battery in {name} is low"))
        ext = inp.external_temps.get(name)
        if ext is not None and inp.now - ext.at > cfg.sensor_stale_after:
            alerts.append(Alert("sensor_stale", name, f"External sensor in {name} stopped reporting"))
        if name in inp.stalled:
            alerts.append(Alert("not_warming", name, f"{name} keeps calling for heat but is not warming up"))
        since = inp.unmet_since.get(name)
        if since is not None and inp.now - since > cfg.target_window:
            alerts.append(Alert("target_not_reached", name, f"{name} is not reaching its target"))
    return tuple(alerts)


def track_unmet(
    previous: Mapping[str, datetime],
    now: datetime,
    room_temps: Mapping[str, float],
    targets: Mapping[str, float],
    margins: Mapping[str, float] | None = None,
) -> dict[str, datetime]:
    """Since when each Room has continuously been below its target by more than its margin
    (caller keeps the result). Pass only targets the boiler is called for (see `wanted_targets`):
    a Room left to drift at setback is not failing to reach anything."""
    margins = margins or {}
    result: dict[str, datetime] = {}
    for room, temp in room_temps.items():
        target = targets.get(room)
        if target is not None and temp < target - margins.get(room, 0.0):
            result[room] = previous.get(room, now)
    return result


HISTORY_LIMIT = 200


@dataclass(frozen=True)
class AlertChanges:
    raised: tuple[Alert, ...] = ()
    cleared: tuple[Alert, ...] = ()


class AlertNotifier:
    """Remembers the active set so each alert is raised once and cleared once."""

    def __init__(self) -> None:
        self._active: dict[tuple[str, str | None], Alert] = {}
        self.history: list[tuple[datetime, Alert]] = []  # every raise, oldest first

    @property
    def active(self) -> tuple[Alert, ...]:
        return tuple(self._active.values())

    def update(self, alerts: tuple[Alert, ...], now: datetime | None = None) -> AlertChanges:
        current = {(a.code, a.room): a for a in alerts}
        raised = tuple(a for k, a in current.items() if k not in self._active)
        if now is not None:
            self.history.extend((now, a) for a in raised)
            del self.history[:-HISTORY_LIMIT]
        cleared = tuple(a for k, a in self._active.items() if k not in current)
        self._active = current
        return AlertChanges(raised, cleared)
