"""Applying a Decision as independent steps: one failing write must not skip the rest.

No Home Assistant imports, so the isolation is unit-tested.
"""

from __future__ import annotations

import logging
from typing import Awaitable, Callable, Sequence

Step = tuple[str, Callable[[], Awaitable[None]]]


async def run_isolated(steps: Sequence[Step], logger: logging.Logger) -> list[str]:
    """Run every step in order; log and continue on failure. Returns the failed step names."""
    failed: list[str] = []
    for name, step in steps:
        try:
            await step()
        except Exception:  # noqa: BLE001 - adapters raise service errors of any type
            logger.exception("Smart Heating step %r failed; continuing", name)
            failed.append(name)
    return failed
