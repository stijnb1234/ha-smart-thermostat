import asyncio
import logging

from custom_components.smart_heating.apply import run_isolated
from custom_components.smart_heating.trv_adapter import TrvAdapter

LOG = logging.getLogger("test")


class FakeServices:
    def __init__(self, failing=()):
        self.calls = []
        self.failing = set(failing)

    async def async_call(self, domain, service, data, blocking=False):
        if data.get("entity_id") in self.failing or data.get("topic") in self.failing:
            raise RuntimeError("boom")
        self.calls.append((domain, service, data))


class FakeHass:
    def __init__(self, failing=()):
        self.services = FakeServices(failing)


def test_failing_step_does_not_skip_later_steps():
    ran = []

    async def bad():
        raise RuntimeError("x")

    async def good():
        ran.append("good")

    failed = asyncio.run(run_isolated([("bad", bad), ("good", good)], LOG))

    assert ran == ["good"] and failed == ["bad"]


def test_one_failing_trv_write_does_not_block_other_trvs_and_is_retried():
    hass = FakeHass(failing={"climate.a"})
    trv = TrvAdapter(hass, {"a": "climate.a", "b": "climate.b"})

    asyncio.run(trv.async_apply({"a": 20.0, "b": 18.0}))

    assert trv.written == {"b": 18.0}
    hass.services.failing.clear()
    asyncio.run(trv.async_apply({"a": 20.0, "b": 18.0}))
    assert trv.written == {"a": 20.0, "b": 18.0}


def test_failed_external_push_is_reported_and_does_not_block_others():
    hass = FakeHass(failing={"zigbee2mqtt/a/set"})
    trv = TrvAdapter(hass, {})

    pushed = asyncio.run(trv.async_push_external_temperature({"a": 19.0, "b": 19.0}, {"a": "a", "b": "b"}))

    assert pushed == {"b"}
