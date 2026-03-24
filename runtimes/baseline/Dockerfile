FROM python:3.12-slim

RUN groupadd --gid 10001 app && useradd --uid 10001 --gid 10001 --create-home --shell /usr/sbin/nologin app

WORKDIR /app
COPY main.py /app/

RUN pip install --no-cache-dir uv

ENV UV_CACHE_DIR=/tmp/uv-cache
ENV XDG_CACHE_HOME=/tmp/.cache

RUN python -m pip install --no-cache-dir fastapi uvicorn

USER 10001:10001

STOPSIGNAL SIGTERM

CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
