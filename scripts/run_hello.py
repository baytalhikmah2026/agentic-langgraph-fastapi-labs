"""Lab 8: run the hello graph once and show what each node wrote into the state."""

import sys

from sovereign_brain.core.settings import get_settings
from sovereign_brain.graphs.hello import build_hello_graph
from sovereign_brain.llm.factory import get_chat_model

DEFAULT_QUESTION = "Summarise this client's exposure to energy stocks."


def main() -> None:
    graph = build_hello_graph(get_chat_model(get_settings()))
    question = " ".join(sys.argv[1:]) or DEFAULT_QUESTION
    for step in graph.stream({"client_id": "C-1042", "question": question}, stream_mode="updates"):
        for node, update in step.items():
            print(f"[{node}]")
            for key, value in update.items():
                print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
