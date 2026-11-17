"""The tool wall and the function-calling format the model receives (Lab 42)."""

from sovereign_brain.tools.portfolio import sector_exposure
from sovereign_brain.tools.registry import RESEARCH_TOOLS, wire_format
from sovereign_brain.tools.risk import stress_test_tool


def test_the_wall_holds_every_local_tool() -> None:
    assert [tool.name for tool in RESEARCH_TOOLS] == [
        "get_positions",
        "sector_exposure",
        "stress_test",
        "run_python",
    ]


def test_the_wire_format_carries_the_pydantic_form() -> None:
    sent = wire_format(stress_test_tool)

    assert sent["type"] == "function"
    assert sent["function"]["name"] == "stress_test"
    parameters = sent["function"]["parameters"]
    assert set(parameters["required"]) == {
        "client_id",
        "sector",
        "sector_value_usd",
        "portfolio_value_usd",
        "shock_percent",
        "risk_profile",
    }
    assert parameters["properties"]["shock_percent"]["maximum"] == 90


def test_langgraph_parameters_stay_hidden_from_the_model() -> None:
    parameters = wire_format(sector_exposure)["function"]["parameters"]

    assert set(parameters["properties"]) == {"client_id", "sector"}
