"""Lab 59: the same questions, answered by three team shapes; what did each one cost?

Run inside the API container (it needs the database and Ollama):
    docker compose exec api python scripts/benchmark_topologies.py
Token counts come from Ollama; times depend on your computer.
"""

import asyncio

from sqlalchemy.ext.asyncio import async_sessionmaker

from sovereign_brain.core.settings import get_settings
from sovereign_brain.db.session import create_engine
from sovereign_brain.graphs.context import ResearchContext
from sovereign_brain.graphs.team.network import build_network_graph
from sovereign_brain.graphs.team.planner import build_planner_graph
from sovereign_brain.graphs.team.supervisor import build_team_graph
from sovereign_brain.llm.factory import get_chat_model
from sovereign_brain.services.benchmark import TopologyRun, measure, summary_table
from sovereign_brain.services.portfolio import PortfolioService

PROFILE = "Amina Rahman Holdings, private-banking, risk profile moderate"
QUESTIONS = [
    "How large is the energy exposure?",
    "Could this client live with a 40% fall in energy stocks?",
]


async def main() -> None:
    settings = get_settings()
    engine = create_engine(settings)
    portfolio = PortfolioService(async_sessionmaker(engine, expire_on_commit=False))
    context = ResearchContext(
        portfolio=portfolio,
        analyst="benchmark",
        max_team_turns=settings.team_max_turns,
        max_replans=settings.planner_max_replans,
    )
    model = get_chat_model(settings)
    shapes = {
        "supervisor": build_team_graph(model),
        "network": build_network_graph(model),
        "planner": build_planner_graph(model),
    }
    runs = []
    for name, graph in shapes.items():
        run = TopologyRun(name)
        for question in QUESTIONS:
            graph_input = {"client_id": "C-1042", "client_profile": PROFILE, "question": question}
            await measure(run, graph, graph_input, context, settings.graph_recursion_limit)
            print(f"{name}: answered '{question}'")
        runs.append(run)
    print(f"\nModel {settings.llm_model}, {len(QUESTIONS)} questions per team shape:\n")
    print(summary_table(runs))
    await engine.dispose()


asyncio.run(main())
