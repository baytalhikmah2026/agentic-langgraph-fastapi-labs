"""The Brain's supervisor (Lab 98): the order of trust, with one more try for bad figures."""

from sovereign_brain.capstone.graph import decide


def test_the_supervisor_keeps_the_order_of_trust() -> None:
    assert decide({}, max_tries=2).next == "extraction"
    assert decide({"facts": {}}, max_tries=2).next == "sanitization"
    assert decide({"facts": {}, "clean": {}}, max_tries=2).next == "analysis"
    written = {"facts": {}, "clean": {}, "draft": {}}
    assert decide({**written, "problems": ["x"], "tries": 1}, max_tries=2).next == "analysis"
    assert decide({**written, "problems": ["x"], "tries": 2}, max_tries=2).next == "finish"
    assert decide({**written, "problems": [], "tries": 1}, max_tries=2).next == "finish"
