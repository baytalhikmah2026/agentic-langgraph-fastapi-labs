"""The run_python tool (Lab 47): checked code goes to the runner, the result comes back."""

import json

import httpx
import pytest
from pydantic import ValidationError

from sovereign_brain.tools.sandbox import run_in_sandbox, run_python


async def test_the_result_of_the_runner_is_returned() -> None:
    sent = []

    def runner(request: httpx.Request) -> httpx.Response:
        sent.append(json.loads(request.content))
        result = {"stdout": "74000.0\n", "stderr": "", "exit_code": 0, "timed_out": False}
        return httpx.Response(200, json=result)

    result = await run_in_sandbox(
        "print(185000 * 0.4)", "http://sandbox.test", transport=httpx.MockTransport(runner)
    )

    assert sent == [{"code": "print(185000 * 0.4)"}]
    assert result["stdout"] == "74000.0\n"


async def test_the_tool_refuses_unchecked_code_before_sending_it() -> None:
    with pytest.raises(ValidationError):
        await run_python.ainvoke({"code": "import socket"})
