FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV PATH="/app/.venv/bin:${PATH}"

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv && \
    uv sync --frozen --no-dev --no-install-project

COPY alembic.ini ./
COPY alembic ./alembic/
COPY apps /app/apps
COPY runtimes /app/runtimes
COPY deploy /app/deploy

EXPOSE 8000

CMD ["uvicorn", "apps.control_plane.src.interfaces.http.main:app", "--host", "0.0.0.0", "--port", "8000"]
