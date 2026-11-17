"""The first wall of the sandbox (Lab 47): code is read and checked before it leaves the API."""

import pytest
from pydantic import ValidationError

from sovereign_brain.tools.sandbox import CodeRequest


def test_a_plain_calculation_passes() -> None:
    code = "import math\nprint(round(185000 * 0.4 / math.sqrt(4), 2))"

    assert CodeRequest(code=code).code == code


@pytest.mark.parametrize(
    "code",
    [
        "import os\nprint(os.listdir('/'))",  # a module outside the list
        "from subprocess import run",  # a module outside the list, other import form
        "print(open('/etc/passwd').read())",  # a dangerous built-in
        "print(().__class__.__bases__)",  # a double-underscore trick
        "print(1 +",  # not valid Python
    ],
)
def test_risky_or_broken_code_is_refused(code: str) -> None:
    with pytest.raises(ValidationError):
        CodeRequest(code=code)
