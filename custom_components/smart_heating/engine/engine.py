from __future__ import annotations

from .models import Decision, EngineInput


def decide(inp: EngineInput) -> Decision:
    """Return desired TRV setpoints, EasyControl setpoint and alerts.

    Skeleton: no demand source exists yet, so every Room is at setback and the
    boiler call stays low.
    """
    return Decision(
        trv_setpoints={room.name: room.setback for room in inp.config.rooms},
        easycontrol_setpoint=inp.config.easycontrol_low,
    )
