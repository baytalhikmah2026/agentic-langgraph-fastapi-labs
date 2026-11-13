"""Lab 7: send one question to the chat model chosen by the settings and print the answer."""

import sys

from langchain_core.messages import HumanMessage, SystemMessage

from sovereign_brain.core.settings import get_settings
from sovereign_brain.llm.factory import get_chat_model

DEFAULT_QUESTION = "In two sentences, what does the research desk of a bank do?"


def main() -> None:
    settings = get_settings()
    question = " ".join(sys.argv[1:]) or DEFAULT_QUESTION
    print(f"provider: {settings.llm_provider}   model: {settings.llm_model}")

    model = get_chat_model(settings)
    reply = model.invoke(
        [
            SystemMessage("You are a concise analyst at Crescent Ledger Bank."),
            HumanMessage(question),
        ]
    )
    print(reply.content)
    usage = reply.usage_metadata or {}
    print(f"tokens: {usage.get('input_tokens')} in, {usage.get('output_tokens')} out")


if __name__ == "__main__":
    main()
