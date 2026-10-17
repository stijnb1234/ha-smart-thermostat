from datetime import datetime, timedelta, timezone

import pytest


class FakeClock:
    """Controllable time source for engine tests."""

    def __init__(self, start: datetime) -> None:
        self._now = start

    def now(self) -> datetime:
        return self._now

    def advance(self, **kwargs: float) -> None:
        self._now += timedelta(**kwargs)


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock(datetime(2026, 1, 12, 3, 0, tzinfo=timezone.utc))
