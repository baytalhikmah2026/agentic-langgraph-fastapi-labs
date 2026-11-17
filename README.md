# Sovereign Brain

The AI Research Desk of Crescent Ledger Bank (a fictional, regulated bank).

Analysts send research requests; a team of AI agents looks up internal data, masks personal
data, analyses it and waits for a human to approve the final report. Everything runs on your
own computer: no data leaves the machine.

Built step by step in the course "Enterprise Agentic AI: 100 Labs with LangGraph & FastAPI".
Every lab ends with a Git checkpoint: `lab-01` ... `lab-100`.

## Start the project

You need Git, Docker and uv (see Lab 1).

    uv sync                                   # libraries from uv.lock
    cp .env.example .env                      # Windows PowerShell: Copy-Item .env.example .env
    docker compose up -d --build              # API (port 8000) + Ollama (port 11434)
    docker compose exec ollama ollama pull qwen3:4b
    docker compose exec ollama ollama pull nomic-embed-text:v1.5
    uv run python scripts/seed_db.py          # tables + sample clients
    uv run python scripts/create_user.py amina --full-name "Amina Rahman"
    uv run python scripts/smoke_test.py amina # end-to-end check (asks for the password)
    uv run pytest                             # automatic tests (no model needed)
    docker compose down                       # stop everything

## Load test (Lab 20)

Run these with the stack started and the cache warmed by `scripts/smoke_test.py`.
Set SB_LOAD_TEST_PASSWORD (12+ characters) in the terminal first.

    uv run python scripts/create_load_users.py --count 30
    uv run locust -f locustfile.py --host http://127.0.0.1:8000 --headless --users 30 --spawn-rate 5 --run-time 2m --csv reports/lab20 --html reports/lab20.html
    uv run python scripts/latency_report.py reports/lab20_stats.csv
    uv run python scripts/create_load_users.py --count 30 --disable

## Research graph (Module 3)

Stations: intake, classify (the model chooses the track; word rules as fallback),
analyse and tools (ReAct loop), review (every figure checked, may send the draft back),
explain (general questions). Set SB_RESEARCH_ROUTER=rules to route by the word rules only.

    POST /v1/research            answer (cached)
    POST /v1/research/stream     answer as Server-Sent Events
    POST /v1/research/trace      answer with its audit trail
    GET  /v1/graphs/research/state | /schema | /diagram

## Backups (Lab 33)

Back up the database (clients, users and conversation checkpoints) before changing data:

    bash scripts/backup-db.sh                                        # macOS, Linux
    powershell -ExecutionPolicy Bypass -File scripts/backup-db.ps1   # Windows

## Semantic memory (Lab 38)

Finished answers are stored by meaning in Qdrant (service `qdrant`, dashboard at
http://localhost:6333/dashboard) using the `nomic-embed-text:v1.5` model in Ollama.
Find them again with `GET /v1/memory/recall?client_id=C-1042&question=...`.
Set `SB_SEMANTIC_MEMORY=false` in `.env` to switch it off.
Before a thread expires, it is summarised into Qdrant as a knowledge nugget (Lab 40);
`POST /v1/threads/{thread_id}/archive` does it right away.

## MCP servers (Labs 44-45)

The API starts its MCP servers as small processes and adds their tools to the agent:
`desk` (risk limits, glossary) and `notes` (the research notes in data/research_notes,
behind a path jail). Every MCP call is written to the audit log; every note read or change
also goes to data/audit/notes_audit.jsonl. Choose the servers with `SB_MCP_SERVERS` in `.env`.

## Graph diagram (Lab 27)

The research graph's diagram lives in docs/research_graph.md (GitHub draws it).
Run this after every change to the graph; a test fails while the page is out of date.

    uv run python scripts/export_graph_diagram.py

API documentation: http://127.0.0.1:8000/docs
