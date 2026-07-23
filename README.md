# Agent Failure

An open-source AI agent security lab platform where learners practice realistic attacks and defenses against LLM-powered agents in controlled, instrumented sandbox environments.

Learners interact with deliberately vulnerable AI agent configurations — prompt injection, tool misuse, memory poisoning — while a control plane records every action as structured trace events and an asynchronous evaluator produces instructional feedback.

Project updates and early-access registration are available at [www.agentfailure.com](https://www.agentfailure.com/).

The original hosted application is no longer running. This repository is provided for local use, research, teaching, and community development.

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
deploy/              Environment examples and Kubernetes deployment manifests
scripts/             Local smoke tests and operational utilities
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
uv run pytest -m "not integration"    # Unit tests (no database required)
uv run pytest -m "integration"        # PostgreSQL integration tests
cd apps/frontend && npm test           # Frontend tests
```

## CI

The CI pipeline (`.github/workflows/ci.yml`) runs on push to `main` and all PRs:

- PostgreSQL 17 service container
- Dependency audits: `pip-audit`, `npm audit`
- Frontend: Biome, TypeScript, ESLint, Vitest
- Backend: Ruff, mypy, Pyright, pytest
- Kubernetes manifest rendering for all included overlays

## License

Licensed under the [Apache License 2.0](./LICENSE).

The license covers the software and documentation, but it does not grant rights to use the Agent Failure name or branding except as described in [TRADEMARKS.md](./TRADEMARKS.md).

## Contributing

Contributions are welcome. Read [CONTRIBUTING.md](./CONTRIBUTING.md) before opening an issue or pull request. Participation is governed by the [Code of Conduct](./CODE_OF_CONDUCT.md).

Please report security vulnerabilities privately as described in [SECURITY.md](./SECURITY.md).
