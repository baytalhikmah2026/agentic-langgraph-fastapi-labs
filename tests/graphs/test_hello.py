from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from sovereign_brain.graphs.hello import build_hello_graph, prepare_brief


def test_prepare_brief_is_deterministic() -> None:
    update = prepare_brief({"client_id": "C-1042", "question": "Energy exposure?"})

    assert update == {"brief": "Client C-1042: Energy exposure?"}


async def test_graph_fills_brief_and_answer() -> None:
    model = GenericFakeChatModel(messages=iter([AIMessage("Energy is 12% of the portfolio.")]))
    graph = build_hello_graph(model)

    result = await graph.ainvoke({"client_id": "C-1042", "question": "Energy exposure?"})

    assert result == {
        "client_id": "C-1042",
        "question": "Energy exposure?",
        "brief": "Client C-1042: Energy exposure?",
        "answer": "Energy is 12% of the portfolio.",
    }
