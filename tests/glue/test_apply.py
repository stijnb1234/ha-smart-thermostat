import logging

from custom_components.smart_heating.apply import run_isolated
from custom_components.smart_heating.trv_adapter import TrvAdapter
from custom_components.smart_heating.trv_devices import TrvDevice

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


async def test_failing_step_does_not_skip_later_steps():
    ran = []

    async def bad():
        raise RuntimeError("x")

    async def good():
        ran.append("good")

    failed = await run_isolated([("bad", bad), ("good", good)], LOG)

    assert ran == ["good"] and failed == ["bad"]


async def test_one_failing_trv_write_does_not_block_other_trvs_and_is_retried():
    hass = FakeHass(failing={"climate.a"})
    trv = TrvAdapter(hass, {"a": TrvDevice("climate.a"), "b": TrvDevice("climate.b")})

    await trv.async_apply({"a": 20.0, "b": 18.0})

    assert trv.written == {"b": 18.0}
    hass.services.failing.clear()
    await trv.async_apply({"a": 20.0, "b": 18.0})
    assert trv.written == {"a": 20.0, "b": 18.0}


async def test_failed_external_push_is_reported_and_does_not_block_others():
    hass = FakeHass(failing={"zigbee2mqtt/a/set"})
    trv = TrvAdapter(
        hass,
        {
            "a": TrvDevice("climate.a", mqtt_topic="zigbee2mqtt/a/set"),
            "b": TrvDevice("climate.b", mqtt_topic="zigbee2mqtt/b/set"),
        },
    )

    pushed = await trv.async_push_external_temperature({"a": 19.0, "b": 19.0})

    assert pushed == {"b"}


async def test_external_temperature_goes_to_the_number_entity_when_the_trv_has_one():
    hass = FakeHass()
    trv = TrvAdapter(
        hass,
        {
            "a": TrvDevice("climate.a", external_number="number.a_external_temperature"),
            "b": TrvDevice("climate.b"),  # takes no external temperature: nothing to do
        },
    )

    pushed = await trv.async_push_external_temperature({"a": 19.04, "b": 19.0})

    assert pushed == {"a", "b"}
    assert hass.services.calls == [
        ("number", "set_value", {"entity_id": "number.a_external_temperature", "value": 19.0})
    ]


async def test_a_hanging_service_call_times_out_instead_of_stalling_the_cycle():
    import asyncio

    from custom_components.smart_heating.apply import call_service

    class Hanging:
        class services:
            @staticmethod
            async def async_call(*args, **kwargs):
                await asyncio.sleep(10)

    try:
        await call_service(Hanging, "climate", "set_temperature", {}, timeout=0.01)
    except TimeoutError:
        timed_out = True
    else:
        timed_out = False
    assert timed_out


async def test_boiler_adapter_counts_a_timeout_as_a_failed_write(monkeypatch):
    import asyncio

    from custom_components.smart_heating import apply
    from custom_components.smart_heating.boiler_adapter import ThermostatBoilerAdapter

    class Slow(FakeServices):
        async def async_call(self, *args, **kwargs):
            await asyncio.sleep(10)

    hass = FakeHass()
    hass.services = Slow()
    adapter = ThermostatBoilerAdapter(hass, "climate.ec")
    monkeypatch.setattr(apply.call_service, "__defaults__", (0.01,))  # timeout in seconds

    await adapter.async_apply(22.0)

    assert adapter.last_write.status == "error" and adapter.last_write.consecutive_failures == 1
    assert adapter.commands.boiler_setpoint is None


async def test_unchanged_setpoint_is_only_rewritten_when_forced():
    hass = FakeHass()
    trv = TrvAdapter(hass, {"a": TrvDevice("climate.a")})
    await trv.async_apply({"a": 20.0})
    calls = len(hass.services.calls)

    await trv.async_apply({"a": 20.0})
    assert len(hass.services.calls) == calls
    await trv.async_apply({"a": 20.0}, force={"a"})
    assert len(hass.services.calls) == calls + 1


async def test_previous_is_value_before_change_and_kept_on_forced_rewrite():
    hass = FakeHass()
    hass.states.data["climate.a"] = FakeState(16.0)
    trv = TrvAdapter(hass, {"a": TrvDevice("climate.a")})

    await trv.async_apply({"a": 20.0})
    await trv.async_apply({"a": 20.0}, force={"a"})

    assert trv.previous == {"a": 16.0} and "a" in trv.written_at
    assert trv.observed("a") == 16.0
