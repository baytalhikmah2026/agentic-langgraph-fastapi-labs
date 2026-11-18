"""Lab 92: the same questions to two model servers, side by side: Ollama and NVIDIA NIM.

Usage: uv run python scripts/compare_inference.py [rounds]   (default 3)
The second server is read from SB_NIM_BASE_URL, SB_NIM_API_KEY and SB_NIM_MODEL (.env).
"""

import os
import sys
import time

from dotenv import dotenv_values
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import SecretStr

from sovereign_brain.core.settings import Settings, get_settings
from sovereign_brain.llm.factory import get_chat_model

QUESTION = "In three sentences, explain what a sector exposure limit is for a bank's client."


def nim_settings(settings: Settings) -> Settings:
    """The same settings, pointed at NIM through the OpenAI-compatible door (Lab 7)."""
    env = {**dotenv_values(".env"), **os.environ}  # .env first, the shell's values win
    return settings.model_copy(
        update={
            "llm_provider": "openai",
            "llm_model": env.get("SB_NIM_MODEL") or "meta/llama-3.1-8b-instruct",
            "openai_base_url": env.get("SB_NIM_BASE_URL") or "http://localhost:8002/v1",
            "openai_api_key": SecretStr(env.get("SB_NIM_API_KEY") or "not-needed"),
            "openai_extra_body": {},  # NIM doesn't need Qwen's "thinking" switch
        }
    )


def measure(settings: Settings, rounds: int) -> tuple[float, float]:
    """Average seconds per answer and output tokens per second over a few rounds."""
    model = get_chat_model(settings)
    messages = [SystemMessage("You are a concise analyst."), HumanMessage(QUESTION)]
    model.invoke(messages)  # a warm-up round: the first call also loads the model
    seconds = tokens = 0.0
    for _ in range(rounds):
        started = time.perf_counter()
        reply = model.invoke(messages)
        seconds += time.perf_counter() - started
        tokens += (reply.usage_metadata or {}).get("output_tokens", 0)
    return seconds / rounds, tokens / seconds


def main(rounds: int) -> None:
    ollama = get_settings()
    print(f"{'server':<8} {'model':<28} {'s per answer':>12} {'tokens/s':>9}")
    for name, settings in (("ollama", ollama), ("nim", nim_settings(ollama))):
        per_answer, speed = measure(settings, rounds)
        print(f"{name:<8} {settings.llm_model:<28} {per_answer:>12.1f} {speed:>9.1f}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 3)
