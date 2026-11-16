from datetime import datetime

from sovereign_brain.graphs.trail import mark, stations


def test_mark_makes_one_timed_entry() -> None:
    entries = mark("classify", "Route: general")

    assert len(entries) == 1
    assert entries[0]["node"] == "classify"
    assert entries[0]["note"] == "Route: general"
    assert datetime.fromisoformat(entries[0]["at"]).tzinfo is not None
    assert stations(entries + mark("explain", "General answer written")) == [
        "classify",
        "explain",
    ]
