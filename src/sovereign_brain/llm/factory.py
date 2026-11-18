"""The one place in the project that creates the AI models: chat (Lab 6) and embeddings (Lab 38)."""

from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel
from langchain_ollama import ChatOllama, OllamaEmbeddings
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
            extra_body=settings.openai_extra_body or None,  # Lab 92: set per server
        )
    return ChatOllama(
        model=settings.llm_model,
        base_url=settings.ollama_base_url,
        temperature=settings.llm_temperature,
        reasoning=False,
    )


def get_embeddings(settings: Settings) -> Embeddings:
    """The embedding model: turns a text into a vector of numbers that captures its meaning."""
    return OllamaEmbeddings(model=settings.embedding_model, base_url=settings.ollama_base_url)
