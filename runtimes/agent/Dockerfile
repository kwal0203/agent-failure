FROM python:3.12-slim

RUN groupadd --gid 10001 app && useradd --uid 10001 --gid 10001 --create-home --shell /usr/sbin/nologin app
WORKDIR /app

COPY runtimes/agent /app/runtimes/agent
COPY apps/agent_harness /app/apps/agent_harness
COPY apps/contracts /app/apps/contracts

RUN python -m pip install --no-cache-dir fastapi uvicorn pydantic pydantic-settings python-dotenv httpx

ENV PYTHONPATH=/app

USER 10001:10001
STOPSIGNAL SIGTERM

CMD ["python", "-m", "uvicorn", "runtimes.agent.main:app", "--host", "0.0.0.0", "--port", "8000"]
