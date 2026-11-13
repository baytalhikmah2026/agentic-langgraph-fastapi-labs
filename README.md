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
    uv run python scripts/smoke_test.py       # end-to-end check
    uv run pytest                             # automatic tests (no model needed)
    docker compose down                       # stop everything

API documentation: http://127.0.0.1:8000/docs
