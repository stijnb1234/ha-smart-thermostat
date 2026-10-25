"""Applying a Decision as independent steps: one failing write must not skip the rest.

No Home Assistant imports, so the isolation is unit-tested.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable, Sequence
from typing import Any

Step = tuple[str, Callable[[], Awaitable[None]]]


async def run_isolated(steps: Sequence[Step], logger: logging.Logger) -> list[str]:
    """Run every step in order; log and continue on failure. Returns the failed step names."""
    failed: list[str] = []
    for name, step in steps:
        try:
            await step()
        except Exception:
            logger.exception("Smart Heating step %r failed; continuing", name)
            failed.append(name)
    return failed


# A service call that hangs (a cloud thermostat, a stuck integration) must not stall the cycle.
SERVICE_TIMEOUT_SECONDS = 30.0


async def call_service(
    hass: Any,
    domain: str,
    service: str,
    data: dict[str, Any],
    timeout: float = SERVICE_TIMEOUT_SECONDS,
) -> None:
    """`hass.services.async_call(..., blocking=True)`, raising TimeoutError after `timeout` s."""
    async with asyncio.timeout(timeout):
        await hass.services.async_call(domain, service, data, blocking=True)
