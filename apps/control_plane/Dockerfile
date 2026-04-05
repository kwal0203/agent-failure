FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv && uv sync --frozen --no-dev

COPY apps /app/apps
COPY runtimes /app/runtimes
COPY deploy /app/deploy
COPY scripts /app/scripts

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "apps.control_plane.src.interfaces.http.main:app", "--host", "0.0.0.0", "--port", "8000"]
