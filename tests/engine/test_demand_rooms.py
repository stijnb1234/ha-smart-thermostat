from custom_components.smart_heating.engine import decide
from custom_components.smart_heating.engine.boiler import demand_rooms
from tests.engine.test_boiler_call import make_input


def test_decision_lists_rooms_causing_demand(clock):
    inp = make_input(clock, temps={"bedroom": 17.0, "office": 19.5})
    assert decide(inp).demand_rooms == ("bedroom",)


def test_no_demand_within_hysteresis(clock):
    inp = make_input(clock)
    targets = {"bedroom": 19.5, "office": 19.5}
    assert demand_rooms(inp.config, targets, {"bedroom": 19.4, "office": 19.4}) == ()
    assert demand_rooms(inp.config, targets, {"bedroom": 18.0}) == ("bedroom",)
