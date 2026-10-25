"""Open-window detection versus a radiator cooling down (simulation).

The TRV's own sensor sits on the valve, a hand's width from the radiator. While the radiator
is hot it reads several degrees above the room; when the boiler call ends the radiator cools
and that reading falls fast although the room itself does not cool. These tests model that
with an exponential decay and check it is not taken for an open window.
"""

import math
from datetime import timedelta

from custom_components.smart_heating.engine import Commands

from .test_controller import T0, make, snap

START = T0 + timedelta(hours=6)  # Monday 09:00, inside the room's comfort window (20 degC)
TRV_EXCESS = 3.5  # K the TRV sensor reads above the room while the radiator is hot
TAU = 35.0  # minutes: cooling time constant of a cast-iron radiator


def _run(c, minutes, room, trv, start):
    reasons = []
    for m in range(minutes):
        now = start + timedelta(minutes=m)
        cycle = c.step(snap(now, temp=trv(m), ext=room(m)))
        c.confirm(cycle, dict(cycle.decision.trv_setpoints), Commands())
        reasons.append(cycle.decision.reasons["work"])
    return reasons


def _heat_then_stop(c):
    """Heat for 30 min (room 19.5, below the demand band: the boiler is called), then stop."""
    _run(c, 30, room=lambda m: 19.5, trv=lambda m: 19.5 + TRV_EXCESS, start=START)
    return START + timedelta(minutes=30)


def test_radiator_cooling_after_the_call_is_not_an_open_window():
    c = make()
    stopped = _heat_then_stop(c)

    # Room reached comfort: the call ends; the room stays at 20 while the radiator cools.
    reasons = _run(
        c, 45, room=lambda m: 20.0, trv=lambda m: 20.0 + TRV_EXCESS * math.exp(-m / TAU), start=stopped
    )

    assert "window" not in reasons


def test_without_the_cooldown_rule_the_same_curve_would_look_like_an_open_window():
    # The TRV falls 1.2 K in the first 15 min: above the default 0.8 K drop. This is the
    # false trigger the cooldown rule exists for.
    drop = TRV_EXCESS * (1 - math.exp(-15 / TAU))
    assert drop > 0.8


def test_open_window_during_cooldown_is_still_seen_by_the_room_sensor():
    c = make()
    stopped = _heat_then_stop(c)

    reasons = _run(
        c,
        10,
        room=lambda m: 20.0 - 0.3 * m,  # the room air cools fast: a real open window
        trv=lambda m: 20.0 + TRV_EXCESS * math.exp(-m / TAU) - 0.3 * m,
        start=stopped,
    )

    assert "window" in reasons


def test_open_window_after_cooldown_is_seen_by_the_trv_sensor():
    c = make()
    stopped = _heat_then_stop(c)
    cooled = 20.0 + TRV_EXCESS * math.exp(-90 / TAU)
    quiet = _run(c, 90, room=lambda m: 20.0, trv=lambda m: 20.0 + TRV_EXCESS * math.exp(-m / TAU), start=stopped)
    assert "window" not in quiet

    reasons = _run(
        c, 10, room=lambda m: 20.0, trv=lambda m: cooled - 0.3 * m, start=stopped + timedelta(minutes=90)
    )

    assert "window" in reasons
