"""The model factory (Labs 7, 92): each OpenAI-compatible server gets the extra fields it knows."""

from sovereign_brain.core.settings import Settings
from sovereign_brain.llm.factory import get_chat_model


def test_extra_fields_follow_the_settings() -> None:
    vllm = Settings(_env_file=None, llm_provider="openai")
    nim = Settings(_env_file=None, llm_provider="openai", openai_extra_body={})

    assert get_chat_model(vllm).extra_body == {"chat_template_kwargs": {"enable_thinking": False}}
    assert get_chat_model(nim).extra_body is None  # NIM: nothing extra is sent
