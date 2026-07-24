FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV PATH="/app/.venv/bin:${PATH}"

RUN groupadd --gid 10001 app && useradd --uid 10001 --gid 10001 --create-home --shell /usr/sbin/nologin app
WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv && \
    uv sync --frozen --no-dev --no-install-project

COPY runtimes/agent /app/runtimes/agent
COPY apps/agent_harness /app/apps/agent_harness
COPY apps/contracts /app/apps/contracts
COPY apps/shared /app/apps/shared

USER 10001:10001
STOPSIGNAL SIGTERM

CMD ["uvicorn", "runtimes.agent.main:app", "--host", "0.0.0.0", "--port", "8000"]
