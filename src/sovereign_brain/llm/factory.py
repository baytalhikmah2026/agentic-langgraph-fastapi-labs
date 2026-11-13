"""The one place in the project that creates the AI chat model."""

from langchain_core.language_models import BaseChatModel
from langchain_ollama import ChatOllama

from sovereign_brain.core.settings import Settings


def get_chat_model(settings: Settings) -> BaseChatModel:
    return ChatOllama(
        model=settings.llm_model,
        base_url=settings.ollama_base_url,
        temperature=settings.llm_temperature,
        reasoning=False,
    )
