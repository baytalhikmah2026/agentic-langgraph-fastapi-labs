"""Shared test setup (Lab 17). Lab 19 adds the full set of fixtures."""

import pytest

from sovereign_brain.core.rate_limit import limiter


@pytest.fixture(autouse=True)
def reset_rate_limits() -> None:
    """Every test starts with empty rate-limit counters."""
    limiter.reset()
