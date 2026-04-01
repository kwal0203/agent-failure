FROM python:3.12-slim

RUN groupadd --gid 10001 app && useradd --uid 10001 --gid 10001 --create-home --shell /usr/sbin/nologin app
WORKDIR /app

# Copy runtime and shared modules
COPY runtimes/baseline /app/runtimes/baseline
COPY apps/agent_harness /app/apps/agent_harness
COPY apps/contracts /app/apps/contracts

# Install dependencies needed by baseline and harness path
RUN python -m pip install --no-cache-dir fastapi uvicorn pydantic python-dotenv httpx

ENV PYTHONPATH=/app

USER 10001:10001
STOPSIGNAL SIGTERM

CMD ["python", "-m", "uvicorn", "runtimes.baseline.main:app", "--host", "0.0.0.0", "--port", "8000"]

# COPY main.py /app/

# RUN pip install --no-cache-dir uv

# ENV UV_CACHE_DIR=/tmp/uv-cache
# ENV XDG_CACHE_HOME=/tmp/.cache

# RUN python -m pip install --no-cache-dir fastapi uvicorn



# CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
