# 👋 Welcome to the Enterprise Agentic AI: 100 Labs with LangGraph & FastAPI Labs!

This is the companion code for the Udemy course **Enterprise Agentic AI: 100 Labs with LangGraph & FastAPI** by Bayt Al Hikmah. Over 100 hands-on labs you'll build the AI Research Desk of a bank, a team of AI agents with LangGraph behind FastAPI that grows from your laptop to a sealed, air-gapped Kubernetes cluster, one small step at a time. 🛠️

Every lab has its own snapshot, so if you ever get stuck or just want to peek ahead, the finished code for that lab is one click away. 🙂

## 🧰 What you'll use

Python 3.13 · uv 0.13.7 · FastAPI 0.162 · LangGraph 1.2 · LangChain 1.4 · Ollama (qwen3:4b, runs on your own computer) · MCP 1.30 · PostgreSQL 18 · Redis 8 · Qdrant 1.20 · Docker Compose · Kubernetes 1.37 (kind) · Traefik · KEDA · Argo Rollouts · Terraform 1.17

## 🚀 How to use the snapshots

- **Just want to look?** Click any lab below. It opens the code as it is at the end of that lab.
- **Want to start a lab from the previous one?** Clone the repository and jump to that lab's snapshot (the tags run from `lab-01` to `lab-100`). For example, to start Lab 13 from the end of Lab 12:

```bash
git clone https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs.git
cd agentic-langgraph-fastapi-labs
git checkout lab-12
```

## Module 1: Foundations & Sovereign Environment Setup

- [Lab 1: Architecting the Zero-Trust Development Environment](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-01)
- [Lab 2: The Precision Scalpel—Bootstrapping Python 3.13](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-02)
- [Lab 3: Initializing the FastAPI Asynchronous Core](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-03)
- [Lab 4: The Sentinel of Data — Implementing Pydantic v2 Models](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-04)
- [Lab 5: Configuring Docker and Docker Compose for Local Dev](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-05)
- [Lab 6: Establishing the LangChain & LangGraph Base Installations](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-06)
- [Lab 7: The Sovereign Core—Connecting Local Open-Weights Models via vLLM](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-07)
- [Lab 8: Building the First "Hello World" Synchronous Graph](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-08)
- [Lab 9: Testing the Graph via FastAPI Endpoints](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-09)
- [Lab 10: The Module 1 Milestone – Orchestrated Ignition](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-10)

## Module 2: Advanced FastAPI & Asynchronous Architecture

- [Lab 11: Refactoring for Asynchronous Execution in FastAPI](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-11)
- [Lab 12: Implementing Dependency Injection for Database Sessions](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-12)
- [Lab 13: Designing Global Exception Handlers for Agentic Failures](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-13)
- [Lab 14: Building Middleware for Request ID Tracking across Agents](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-14)
- [Lab 15: Integrating Server-Sent Events (SSE) for Real-Time Streaming](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-15)
- [Lab 16: Securing Endpoints with OAuth2 and JWT](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-16)
- [Lab 17: Implementing Rate Limiting for Expensive LLM Calls](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-17)
- [Lab 18: Configuring Redis for API Caching](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-18)
- [Lab 19: Writing Comprehensive Pytest Fixtures for the API](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-19)
- [Lab 20: Module 2 Milestone: Stress-Testing the Async Backbone](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-20)

## Module 3: LangGraph Core Mechanics

- [Lab 21: The Architect’s Blueprint: Mastering the TypedDict State in LangGraph](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-21)
- [Lab 22: Building Single-Node Graphs: The ReAct Pattern](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-22)
- [Lab 23: Designing Conditional Edges for Dynamic Routing](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-23)
- [Lab 24: Implementing Cyclic Graphs for Iterative Reasoning](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-24)
- [Lab 25: Handling Graph Input and Output Schemas](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-25)
- [Lab 26: Managing State Reducers for Append-Only Memory](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-26)
- [Lab 27: Visualizing the Graph Architecture Programmatically](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-27)
- [Lab 28: Injecting Dependencies into LangGraph Nodes](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-28)
- [Lab 29: Unit Testing Individual Graph Nodes](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-29)
- [Lab 30: The Multi-Path Architect — Deploying an Enterprise Routing Engine](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-30)

## Module 4: Stateful Memory & Checkpointing

- [Lab 31: Mastering the "Infinite Thread" — Implementing Thread-Level Memory](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-31)
- [Lab 32: Persistence is Power — Implementing SQLite Checkpointers](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-32)
- [Lab 33: Migrating to PostgreSQL for Production Checkpointing](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-33)
- [Lab 34: Managing Session Expiration and Garbage Collection](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-34)
- [Lab 35: The Art of Persistence: Resuming Graphs via Historical Checkpoints](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-35)
- [Lab 36: Temporal Architectures—Mastering "Time Travel" and State Rewinding](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-36)
- [Lab 37: Modifying Historical State and Forking Executions](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-37)
- [Lab 38: The Infinite Vault: Integrating Qdrant for Semantic Agentic Memory](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-38)
- [Lab 39: Hybridizing Episodic (Thread) and Semantic (Vector) Memory](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-39)
- [Lab 40: Module 4 Milestone: The Infinite-Memory Conversational Agent](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-40)

## Module 5: Tool Binding & Execution (The MCP Standard)

- [Lab 41: Designing Deterministic Custom Tools with Pydantic](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-41)
- [Lab 42: Binding Tools to the LLM (Function Calling Standards)](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-42)
- [Lab 43: The Resilience Protocol – Handling Tool Execution Errors Gracefully](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-43)
- [Lab 44: Implementing the Model Context Protocol (MCP) Base](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-44)
- [Lab 45: Building MCP Servers for Local File System Access](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-45)
- [Lab 46: Secure Enterprise API Integration via the Model Context Protocol (MCP)](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-46)
- [Lab 47: Executing Code in Sandboxed Environments (gVisor)](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-47)
- [Lab 48: Parallel Tool Calling for Latency Reduction](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-48)
- [Lab 49: Enterprise-Grade Determinism: Forcing Tool Outputs](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-49)
- [Lab 50: Module 5 Milestone — The Autonomous Research Assistant](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-50)

## Module 6: Multi-Agent Topologies

- [Lab 51: The Supervisor Pattern: Architecting the Managing Agent](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-51)
- [Lab 52: The Hierarchical Team Pattern—Sub-Graphs as Nodes](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-52)
- [Lab 53: The Network Pattern — Peer-to-Peer Agent Negotiation](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-53)
- [Lab 54: State Sharing Across Multiple Isolated Graphs](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-54)
- [Lab 55: Designing a "Critic" Agent for Self-Correction](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-55)
- [Lab 56: Building a "Planner" Agent for Long-Horizon Tasks](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-56)
- [Lab 57: Implementing the "Map-Reduce" Pattern for Large Document Analysis](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-57)
- [Lab 58: Resolving the Gridlock — Detecting and Breaking Deadlocks](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-58)
- [Lab 59: Benchmarking Multi-Agent Topologies for Token Efficiency](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-59)
- [Lab 60: The Software Development Agency Topology](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-60)

## Module 7: Human-in-the-Loop (HITL) & Observability

- [Lab 61: Implementing Explicit Pauses (Interrupt Before)](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-61)
- [Lab 62: Implementing Explicit Pauses (Interrupt After)](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-62)
- [Lab 63: Building a FastAPI Endpoint to Approve/Reject Actions](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-63)
- [Lab 64: Injecting Human Feedback into the State Object](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-64)
- [Lab 65: The Executive Override: Modifying Agent Trajectory](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-65)
- [Lab 66: Integrating OpenTelemetry for End-to-End Tracing](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-66)
- [Lab 67: The X-Ray Vision of AI—Instrumenting LangGraph Execution in LangSmith](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-67)
- [Lab 68: Exporting Custom Metrics to Prometheus](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-68)
- [Lab 69: Building Agentic Dashboards in Grafana](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-69)
- [Lab 70: The Auditable, Human-Guided Workflow](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-70)

## Module 8: Security, Cryptography & Compliance

- [Lab 71: Implementing Prompt Injection Defense Mechanisms](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-71)
- [Lab 72: Masking PII Data before LLM Inference](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-72)
- [Lab 73: Enforcing Role-Based Access Control (RBAC) in Graphs](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-73)
- [Lab 74: Establishing mTLS for Inter-Agent Network Communication](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-74)
- [Lab 75: Securing API Keys with HashiCorp Vault in Multi-Agent Systems](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-75)
- [Lab 76: Generating Cryptographic Signatures for Agent Approvals](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-76)
- [Lab 77: Building Immutable Audit Logs for DORA Compliance](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-77)
- [Lab 78: Implementing Data Retention and Deletion Policies (GDPR)](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-78)
- [Lab 79: Red-Teaming the Agentic System (Simulated Attacks)](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-79)
- [Lab 80: The Hardened, Bank-Grade Agent](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-80)

## Module 9: Production Engineering & Kubernetes Orchestration

- [Lab 81: Containerizing LangGraph and FastAPI for Production](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-81)
- [Lab 82: Writing Kubernetes Deployment and Service Manifests](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-82)
- [Lab 83: Elastic Agentic Scaling—Horizontal Pod Autoscalers (HPA)](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-83)
- [Lab 84: Managing ConfigMaps and Secrets in K8s](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-84)
- [Lab 85: Deploying PostgreSQL and Redis StatefulSets](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-85)
- [Lab 86: Implementing Readiness and Liveness Probes for Agents](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-86)
- [Lab 87: Setting up Ingress Controllers with TLS Termination](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-87)
- [Lab 88: Building GitHub Actions CI/CD Pipelines for Graph Updates](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-88)
- [Lab 89: Implementing Blue/Green Deployments for Agent Versions](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-89)
- [Lab 90: Zero-Downtime Cluster Deployment](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-90)

## Module 10: Sovereign Deployment & Decentralized Research

- [Lab 91: Architecting for the Air-Gapped Enterprise Edge](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-91)
- [Lab 92: Deploying NVIDIA NIMs for Local Inference Acceleration](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-92)
- [Lab 93: Fine-Tuning Open Models for Specific Graph Tasks](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-93)
- [Lab 94: Establishing Federated Learning Pipelines across Edge Nodes](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-94)
- [Lab 95: The Compliance Sentinel — Automated Sovereign Reporting](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-95)
- [Lab 96: Capstone Prep: Infrastructure Provisioning with Terraform](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-96)
- [Lab 97: Capstone Prep: Defining the Multi-Agent Schemas](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-97)
- [Lab 98: Capstone Prep: Wiring the High-Availability API](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-98)
- [Lab 99: Capstone Prep: Securing the Final Endpoints](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-99)
- [Lab 100: The Sovereign Enterprise Brain](https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs/tree/lab-100)

## 🛠️ Running the finished project

The AI Research Desk of Crescent Ledger Bank (a fictional, regulated bank).

Analysts send research requests; a team of AI agents looks up internal data, masks personal
data, analyses it and waits for a human to approve the final report. Everything runs on your
own computer: no data leaves the machine.

Built step by step in the course "Enterprise Agentic AI: 100 Labs with LangGraph & FastAPI".
Every lab ends with a Git checkpoint: `lab-01` ... `lab-100`.

### Start the project

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

### Load test (Lab 20)

Run these with the stack started and the cache warmed by `scripts/smoke_test.py`.
Set SB_LOAD_TEST_PASSWORD (12+ characters) in the terminal first.

    uv run python scripts/create_load_users.py --count 30
    uv run locust -f locustfile.py --host http://127.0.0.1:8000 --headless --users 30 --spawn-rate 5 --run-time 2m --csv reports/lab20 --html reports/lab20.html
    uv run python scripts/latency_report.py reports/lab20_stats.csv
    uv run python scripts/create_load_users.py --count 30 --disable

### Research graph (Module 3)

Stations: intake, classify (the model chooses the track; word rules as fallback),
analyse and tools (ReAct loop), review (every figure checked, may send the draft back),
explain (general questions). Set SB_RESEARCH_ROUTER=rules to route by the word rules only.

    POST /v1/research            answer (cached)
    POST /v1/research/stream     answer as Server-Sent Events
    POST /v1/research/trace      answer with its audit trail
    GET  /v1/graphs/research/state | /schema | /diagram

### Backups (Lab 33)

Back up the database (clients, users and conversation checkpoints) before changing data:

    bash scripts/backup-db.sh                                        # macOS, Linux
    powershell -ExecutionPolicy Bypass -File scripts/backup-db.ps1   # Windows

### Semantic memory (Lab 38)

Finished answers are stored by meaning in Qdrant (service `qdrant`, dashboard at
http://localhost:6333/dashboard) using the `nomic-embed-text:v1.5` model in Ollama.
Find them again with `GET /v1/memory/recall?client_id=C-1042&question=...`.
Set `SB_SEMANTIC_MEMORY=false` in `.env` to switch it off.
Before a thread expires, it is summarised into Qdrant as a knowledge nugget (Lab 40);
`POST /v1/threads/{thread_id}/archive` does it right away.

### MCP servers (Labs 44-46)

The API starts its MCP servers as small processes and adds their tools to the agent:
`desk` (risk limits, glossary), `notes` (the research notes in data/research_notes,
behind a path jail) and `market` (prices from the internal market-data API, service
`market` on port 8100, protected by `SB_MARKET_API_TOKEN`). Every MCP call is written to the audit log; every note read or change
also goes to data/audit/notes_audit.jsonl. Choose the servers with `SB_MCP_SERVERS` in `.env`.

### Autonomous Research Assistant (Lab 50)

`POST /v1/assistant` takes a research request and streams its work as Server-Sent Events:
`plan` (research or report), `step`, `tool_call`, `tool_result`, then `answer` or `report`,
and `done`. Every event is a Pydantic model (schemas/assistant.py). Questions that ask for a
"report" use the report graph (`POST /v1/reports/{client_id}`, Lab 49); everything else uses
the research graph with all its tools and MCP servers.

### Software Development Agency (Lab 60)

`POST /v1/agency` runs one development cycle: a project manager writes a spec (file name,
requirements, a short check), a developer writes the file into data/workspace through the
workspace MCP server, and a reviewer runs the file with the check in the sandbox (Lab 47)
until it prints PASS or the rounds run out (SB_MAX_REVISIONS). Only the developer can write
to the workspace: its MCP server is not on the shared tool wall (SB_AGENCY_MCP_SERVERS).

### Kubernetes (Module 9)

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

### The Sovereign Enterprise Brain (Labs 97-100)

A supervisor and three specialists (extraction, sanitization, analysis) in one graph
(capstone/graph.py), with contracts in capstone/schemas.py (published in docs/brain_schemas.json).
Start a run live with `scripts/brain_live.py`, decide with
`POST /v1/brain/runs/{run_id}/decision` (another analyst or a lead), check the sealed record
with `scripts/verify_brain.py <run_id>`, and fetch the signed compliance report with
`scripts/compliance_report.py`. Tokens carry scopes (brain:run, brain:decide); runs have a
budget (SB_BRAIN_RUN_LIMIT) and a step limit (SB_BRAIN_RECURSION_LIMIT).

### Graph diagram (Lab 27)

The research graph's diagram lives in docs/research_graph.md (GitHub draws it).
Run this after every change to the graph; a test fails while the page is out of date.

    uv run python scripts/export_graph_diagram.py

API documentation: http://127.0.0.1:8000/docs

---

Stuck on a lab? Ask in the course Q&A, we read every question. 💬 Enjoy the build! 🎉
