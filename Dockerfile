# syntax=docker/dockerfile:1

# Stage 1: build the virtual environment with uv
FROM python:3.13.18-slim-trixie AS builder
COPY --from=ghcr.io/astral-sh/uv:0.13.7 /uv /uvx /bin/
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=0
WORKDIR /app
# Libraries first: this layer is reused until pyproject.toml or uv.lock changes
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev
# Then our own code
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

# Stage 2: the small image that runs the API, as a normal user
FROM python:3.13.18-slim-trixie AS runtime
# Lab 81: the version and origin travel with the image, readable by any tool
ARG APP_VERSION=0.2.0
LABEL org.opencontainers.image.title="sovereign-brain-api"       org.opencontainers.image.version="$APP_VERSION"       org.opencontainers.image.vendor="Crescent Ledger Bank (lab)"       org.opencontainers.image.source="https://github.com/baytalhikmah2026/agentic-langgraph-fastapi-labs"
RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --no-create-home app
COPY --from=builder --chown=app:app /app /app
# Production unless told otherwise (Compose for development sets SB_ENVIRONMENT=local in .env)
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1 SB_ENVIRONMENT=production
WORKDIR /app
USER app
EXPOSE 8000
CMD ["fastapi", "run", "src/sovereign_brain/main.py", "--host", "0.0.0.0", "--port", "8000"]
