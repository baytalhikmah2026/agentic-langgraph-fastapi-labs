"""The one place in the project that creates the AI chat model."""

from langchain_core.language_models import BaseChatModel
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

from sovereign_brain.core.settings import Settings


def get_chat_model(settings: Settings) -> BaseChatModel:
    if settings.llm_provider == "openai":
        # Any OpenAI-compatible server: vLLM, NVIDIA NIM, or Ollama's /v1 endpoint
        return ChatOpenAI(
            model=settings.llm_model,
            base_url=settings.openai_base_url,
            api_key=settings.openai_api_key,
            temperature=settings.llm_temperature,
            extra_body={"chat_template_kwargs": {"enable_thinking": False}},
        )
    return ChatOllama(
        model=settings.llm_model,
        base_url=settings.ollama_base_url,
        temperature=settings.llm_temperature,
        reasoning=False,
    )
