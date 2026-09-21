# syntax=docker/dockerfile:1
FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy
WORKDIR /app

FROM base AS builder
COPY --from=ghcr.io/astral-sh/uv:0.11.8 /uv /usr/local/bin/uv
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY backend/src ./src
RUN uv sync --frozen --no-dev

FROM base AS runtime
ARG GIT_SHA=dev
ARG BUILT_AT=unknown
ENV GIT_SHA=${GIT_SHA} BUILT_AT=${BUILT_AT} PATH="/app/.venv/bin:$PATH"
RUN useradd --create-home --uid 10001 appuser
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz')"
CMD ["uvicorn", "interview_agent.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
