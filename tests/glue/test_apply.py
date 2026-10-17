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


class FakeState:
    def __init__(self, temperature, state="heat"):
        self.state = state
        self.attributes = {"temperature": temperature}


class FakeStates:
    def __init__(self):
        self.data = {}

    def get(self, entity_id):
        return self.data.get(entity_id)


class FakeHass:
    def __init__(self, failing=()):
        self.services = FakeServices(failing)
        self.states = FakeStates()


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


def test_unchanged_setpoint_is_only_rewritten_when_forced():
    hass = FakeHass()
    trv = TrvAdapter(hass, {"a": "climate.a"})
    asyncio.run(trv.async_apply({"a": 20.0}))
    calls = len(hass.services.calls)

    asyncio.run(trv.async_apply({"a": 20.0}))
    assert len(hass.services.calls) == calls
    asyncio.run(trv.async_apply({"a": 20.0}, force={"a"}))
    assert len(hass.services.calls) == calls + 1


def test_previous_is_value_before_change_and_kept_on_forced_rewrite():
    hass = FakeHass()
    hass.states.data["climate.a"] = FakeState(16.0)
    trv = TrvAdapter(hass, {"a": "climate.a"})

    asyncio.run(trv.async_apply({"a": 20.0}))
    asyncio.run(trv.async_apply({"a": 20.0}, force={"a"}))

    assert trv.previous == {"a": 16.0} and "a" in trv.written_at
    assert trv.observed("a") == 16.0
