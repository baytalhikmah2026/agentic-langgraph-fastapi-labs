import pytest
from pydantic import ValidationError

from sovereign_brain.schemas.research import ResearchRequest

VALID = {"client_id": "c-1042", "question": "Summarise the exposure to energy stocks."}


def test_client_id_is_upper_cased_and_defaults_are_set() -> None:
    request = ResearchRequest.model_validate(VALID)

    assert request.client_id == "C-1042"
    assert request.priority == "normal"
    assert request.max_sources == 3


def test_text_is_not_converted_to_a_number() -> None:
    with pytest.raises(ValidationError) as error:
        ResearchRequest.model_validate({**VALID, "max_sources": "5"})

    assert error.value.errors()[0]["type"] == "int_type"


def test_unknown_fields_are_refused() -> None:
    with pytest.raises(ValidationError) as error:
        ResearchRequest.model_validate({**VALID, "colour": "blue"})

    assert error.value.errors()[0]["type"] == "extra_forbidden"
