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

## MCP servers (Labs 44-46)

The API starts its MCP servers as small processes and adds their tools to the agent:
`desk` (risk limits, glossary), `notes` (the research notes in data/research_notes,
behind a path jail) and `market` (prices from the internal market-data API, service
`market` on port 8100, protected by `SB_MARKET_API_TOKEN`). Every MCP call is written to the audit log; every note read or change
also goes to data/audit/notes_audit.jsonl. Choose the servers with `SB_MCP_SERVERS` in `.env`.

## Autonomous Research Assistant (Lab 50)

`POST /v1/assistant` takes a research request and streams its work as Server-Sent Events:
`plan` (research or report), `step`, `tool_call`, `tool_result`, then `answer` or `report`,
and `done`. Every event is a Pydantic model (schemas/assistant.py). Questions that ask for a
"report" use the report graph (`POST /v1/reports/{client_id}`, Lab 49); everything else uses
the research graph with all its tools and MCP servers.

## Software Development Agency (Lab 60)

`POST /v1/agency` runs one development cycle: a project manager writes a spec (file name,
requirements, a short check), a developer writes the file into data/workspace through the
workspace MCP server, and a reviewer runs the file with the check in the sandbox (Lab 47)
until it prints PASS or the rounds run out (SB_MAX_REVISIONS). Only the developer can write
to the workspace: its MCP server is not on the shared tool wall (SB_AGENCY_MCP_SERVERS).

## Kubernetes (Module 9)

The desk also runs on a local kind cluster. On a new cluster, in this order:

    kind create cluster --config k8s/kind-config.yaml
    # add-ons: metrics-server + its kind patch, KEDA (Lab 83), Traefik (Lab 87), Argo Rollouts (Lab 89)
    docker build -t sovereign-brain-api:0.2.0 .
    kind load docker-image sovereign-brain-api:0.2.0 --name sovereign
    uv run python scripts/make_certs.py          # only if ops/certs is empty (Lab 74)
    kubectl apply -k k8s/overlays/local          # pods wait for their Secrets
    uv run python scripts/k8s_secrets.py
    uv run python scripts/issue_cert.py desk localhost desk.localhost
    kubectl -n sovereign-brain create secret tls desk-tls --cert ops/certs/desk.crt --key ops/certs/desk.key
    kubectl -n sovereign-brain exec deploy/ollama -- ollama pull qwen3:4b
    kubectl -n sovereign-brain exec deploy/ollama -- ollama pull nomic-embed-text:v1.5
    kubectl -n sovereign-brain exec -it svc/api -- python scripts/create_user.py amina --full-name "Amina Rahman"

The desk answers at https://localhost:8443 (curl --cacert ops/certs/ca.crt). Releases are
blue/green: `kubectl argo rollouts promote api`. `scripts/uptime_probe.py` counts failed
requests during a release (Lab 90).

## The Sovereign Enterprise Brain (Labs 97-100)

A supervisor and three specialists (extraction, sanitization, analysis) in one graph
(capstone/graph.py), with contracts in capstone/schemas.py (published in docs/brain_schemas.json).
Start a run live with `scripts/brain_live.py`, decide with
`POST /v1/brain/runs/{run_id}/decision` (another analyst or a lead), check the sealed record
with `scripts/verify_brain.py <run_id>`, and fetch the signed compliance report with
`scripts/compliance_report.py`. Tokens carry scopes (brain:run, brain:decide); runs have a
budget (SB_BRAIN_RUN_LIMIT) and a step limit (SB_BRAIN_RECURSION_LIMIT).

## Graph diagram (Lab 27)

The research graph's diagram lives in docs/research_graph.md (GitHub draws it).
Run this after every change to the graph; a test fails while the page is out of date.

    uv run python scripts/export_graph_diagram.py

API documentation: http://127.0.0.1:8000/docs
