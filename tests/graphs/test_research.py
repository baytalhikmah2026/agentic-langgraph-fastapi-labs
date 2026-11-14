from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from sovereign_brain.graphs.research import build_research_graph, intake

REQUEST = {
    "client_id": "C-1042",
    "client_profile": "Amina Rahman Holdings, private-banking, risk profile moderate",
    "question": "Energy exposure?",
}


def test_intake_writes_the_first_messages() -> None:
    update = intake(REQUEST)

    assert update["steps"] == ["intake"]
    assert update["status"] == "received"
    assert update["messages"][1].content == (
        "Client C-1042 (Amina Rahman Holdings, private-banking, risk profile moderate): "
        "Energy exposure?"
    )


async def test_reducers_append_steps_and_overwrite_status() -> None:
    model = GenericFakeChatModel(messages=iter([AIMessage("Energy is 12% of the portfolio.")]))
    graph = build_research_graph(model)

    result = await graph.ainvoke(REQUEST)

    assert result["steps"] == ["intake", "analyse"]
    assert result["status"] == "answered"
    assert result["answer"] == "Energy is 12% of the portfolio."
    assert [message.type for message in result["messages"]] == ["system", "human", "ai"]
