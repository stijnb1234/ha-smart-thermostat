"""TRV manual changes and lost writes (observed setpoint vs what we wrote)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .models import Alert, EngineInput

TOLERANCE = 0.05
MAX_RETRIES = 3


@dataclass(frozen=True)
class TrvCheck:
    rewrite: frozenset[str]
    manual: Mapping[str, float]
    retries: Mapping[str, int]
    alerts: tuple[Alert, ...]


def _same(a: float, b: float) -> bool:
    return abs(a - b) <= TOLERANCE


def check_trvs(inp: EngineInput, targets: Mapping[str, float]) -> TrvCheck:
    """Decide per Room: rewrite a lost write, leave a hand-set TRV alone, or do nothing.

    Only Rooms whose written setpoint is still the target are examined; when the target
    changes the normal write happens and retry/manual state starts over.
    """
    cmds, now = inp.last_commands, inp.now
    rewrite: set[str] = set()
    manual: dict[str, float] = {}
    retries: dict[str, int] = {}
    alerts: list[Alert] = []
    for room, target in targets.items():
        written = cmds.trv_setpoints.get(room)
        if written is None or not _same(written, target):
            continue
        observed = inp.trv_observed.get(room)
        if observed is None:
            # Unknown right now: keep whatever state we had.
            if room in cmds.trv_manual:
                manual[room] = cmds.trv_manual[room]
            if room in cmds.trv_retries:
                retries[room] = cmds.trv_retries[room]
            continue
        if _same(observed, written):
            continue  # landed: manual/retry state and alert clear
        if room in cmds.trv_manual:
            manual[room] = cmds.trv_manual[room]
            continue
        written_at = cmds.trv_written_at.get(room)
        if written_at is None or now - written_at < inp.config.trv_settle:
            if room in cmds.trv_retries:
                retries[room] = cmds.trv_retries[room]
            continue
        previous = cmds.trv_previous.get(room)
        if previous is None or not _same(observed, previous):
            manual[room] = written
            continue
        used = cmds.trv_retries.get(room, 0)
        retries[room] = used
        if used < MAX_RETRIES:
            rewrite.add(room)
            retries[room] = used + 1
        else:
            alerts.append(
                Alert("trv_write_failed", room, f"TRV in {room} does not accept its setpoint of {target}")
            )
    return TrvCheck(frozenset(rewrite), manual, retries, tuple(alerts))
