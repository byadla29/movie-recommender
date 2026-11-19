# syntax=docker/dockerfile:1
FROM python:3.13-slim

# uv pinned to an exact version for reproducible builds.
COPY --from=ghcr.io/astral-sh/uv:0.13.9 /uv /usr/local/bin/uv

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Install dependencies first (cached layer; only rebuilt when the lockfile changes).
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY alembic.ini docker-entrypoint.sh ./
COPY migrations ./migrations
COPY src ./src
RUN uv sync --frozen --no-dev

# Never run as root inside the container.
RUN useradd --system --uid 10001 --no-create-home app
USER app

EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=5 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/ready', timeout=2)"]
ENTRYPOINT ["sh", "/app/docker-entrypoint.sh"]
