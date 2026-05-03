# Agent Failure

A public AI agent security lab platform where learners practice realistic attacks and defenses against LLM-powered agents in controlled, instrumented sandbox environments. Live at **agentfailure.com**.

Learners interact with deliberately vulnerable AI agent configurations — prompt injection, tool misuse, memory poisoning — while a control plane records every action as structured trace events and an asynchronous evaluator produces instructional feedback.

## Architecture

```
[Learner Browser (React)]
       │  ▲  REST + WebSocket
       ▼  │
[Control Plane (FastAPI)]  ──────►  [PostgreSQL]
       │  ▲
       │  │  HTTP / NDJSON stream
       ▼  │
[Agent Runtime (FastAPI, per-session)]
       │  ▲
       ▼  │
   [LLM (OpenRouter)]
```

## Labs

| # | Name | Attack Vector | Scenario |
|---|------|---------------|----------|
| 1 | Prompt Injection | Indirect prompt injection via email | Trick an email assistant into revealing a protected manager address |
| 2 | Tool Misuse | Runbook manipulation | Get an SRE agent to delete the production database by modifying its ops runbook |
| 3 | Memory Poisoning | Vendor profile memory corruption | Poison vendor memory via email to redirect payments to an attacker account |

## Tech Stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy, Alembic, PostgreSQL 17
- **Frontend:** React 19, TypeScript 5.9, Vite 8 (deployed on Vercel)
- **LLM Gateway:** OpenRouter
- **Package manager:** `uv` (Python), npm (JS)
- **Container runtime:** Docker + Kubernetes
- **Streaming:** WebSocket (learner ↔ control plane), NDJSON (control plane → runtime)

## Project Structure

```
apps/
  agent_harness/     Shared agent abstractions (LLM client, tools, session loop types)
  contracts/         Pydantic schemas, TypeScript types, event definitions, constants
  control_plane/     Central API — auth, sessions, WebSocket streaming, trace persistence
  evaluator/         Async constraint evaluation engine with rule bundles per lab
  frontend/          React SPA — lab catalog, session workspace, feedback timeline
packages/
  authz/             (planned) Authorization logic
  shared-types/      (planned) Shared type extraction
  trace-schema/      (planned) Trace schema extraction
runtimes/
  agent/             Per-session agent runtime — LLM loop, tool dispatch, lab configs
infra/               Kubernetes staging/prod manifests
deploy/              VPS (Docker Compose + Caddy) and K8s deployment configs
scripts/             Build, push, release, and staging automation
docs/                PRD, specs, TDD, lab designs
```

## Getting Started

### Prerequisites

- Python 3.12+
- Node.js 20+
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Docker (for PostgreSQL)

### Local Development

1. **Start PostgreSQL:**
   ```bash
   docker compose up -d db
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your DATABASE_URL, OPENROUTER_API_KEY, etc.
   ```

3. **Install Python dependencies:**
   ```bash
   uv sync --frozen --group dev
   ```

4. **Run database migrations:**
   ```bash
   uv run alembic upgrade head
   ```

5. **Start the control plane:**
   ```bash
   uv run uvicorn apps.control_plane.src.interfaces.http.main:app --host 0.0.0.0 --port 8000 --reload
   ```

6. **Start the agent runtime** (separate terminal):
   ```bash
   uv run uvicorn runtimes.agent.main:app --host 0.0.0.0 --port 8001
   ```

7. **Start the frontend** (separate terminal):
   ```bash
   cd apps/frontend && npm ci && npm run dev
   ```

8. **Start the evaluator worker** (separate terminal, optional):
   ```bash
   uv run python -m apps.evaluator.src.interfaces.runtime.evaluator_worker
   ```

## Testing

```bash
uv run pytest -m "not integration"    # Unit tests
cd apps/frontend && npm test           # Frontend tests
```

## CI

The CI pipeline (`.github/workflows/ci.yml`) runs on push to `main` and all PRs:

- PostgreSQL 17 service container
- Frontend: Biome lint, TypeScript type check
- Backend: mypy, Pyright, pytest

## License

This project is proprietary and **not open source**.

All rights reserved. No permission is granted to use, copy, modify, or distribute this code.

See [LICENSE](./LICENSE) for full terms.

## Contributing

Contributions are not accepted without prior written approval from the project owner.
