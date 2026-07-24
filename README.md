# Agent Failure

An open-source AI agent security lab platform where learners practice realistic attacks and defenses against LLM-powered agents in controlled, instrumented sandbox environments.

Learners interact with deliberately vulnerable AI agent configurations — prompt injection, tool misuse, memory poisoning — while a control plane records every action as structured trace events and an asynchronous evaluator produces instructional feedback.

Project updates and early-access registration are available at [www.agentfailure.com](https://www.agentfailure.com/).

The original hosted application is no longer running. This repository is provided for local use, research, teaching, and community development.

## Project status

Agent Failure is an experimental open-source release of a former commercial
MVP. Version 0.1.0 is intended for evaluation, research, and controlled
teaching environments; it is not a supported hosted service or a
production-ready security boundary.

The labs deliberately execute unsafe agent behavior. Run them only with test
credentials and disposable infrastructure, and do not expose session runtimes
directly to the public internet.

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

### Runtime lifecycle

Each Kubernetes agent runtime is a disposable, single-process Pod assigned to
exactly one session. The control plane injects that session UUID into the Pod,
and the runtime rejects requests for any other session. Transcripts, inbox
items, simulated files, and invoice memory are intentionally ephemeral:

- concurrent turns are serialized and mutable tool state is lock-protected;
- state is discarded when the runtime process exits;
- a Pod restart does not restore an interrupted session;
- scaling is performed by provisioning more per-session Pods, not by adding
  workers to one runtime process.

This isolation model is deliberate. Durable session lifecycle, trace, evidence,
and report data belongs to the control plane and PostgreSQL. When using the
single local runtime command below, restart that process before starting a
different lab session.

### Evaluator

The evaluator uses deterministic, trace-backed constraints inspired by
constraint-based modeling. Assessment, evidence, pedagogical presentation, and
learner-facing feedback are separate layers. Rule-bundle versions are persisted
with evaluation results so historical outcomes remain attributable when
scoring behavior changes. LLM classification is limited to interpreting
specific simulated artifacts; recorded trace evidence remains authoritative.

### Simulated telemetry

Lab 2's operational alerts are intentionally simulated scenario data. They are
defined and timestamped by the per-session runtime, persisted by the control
plane as `SIMULATED_TELEMETRY_SIGNAL` trace events, and replayed to the browser
from PostgreSQL. The frontend does not fabricate or schedule telemetry.

### Lab identities

Lab identity and lab-version identity are separate persisted values. The
authoritative production definitions live in
`apps/contracts/src/lab_identities.py`; the frontend consumes the generated
`apps/frontend/src/labIdentities.generated.ts` artifact.

| Lab slug | Lab ID | Active version ID | Runtime config alias | Objective keys |
|---|---|---|---|---|
| `agent-prompt-injection` | `44444444-4444-4444-4444-444444444444` | `44444444-4444-4444-4444-aaaaaaaaaaa1` | `11111111-1111-1111-1111-111111111111` | `malicious_email_injected`, `malicious_instructions_entered_context`, `token_exposed` |
| `agent-tool-misuse` | `55555555-5555-5555-5555-555555555555` | `55555555-5555-5555-5555-aaaaaaaaaaa2` | `22222222-2222-2222-2222-222222222222` | `unsafe_tool_invocation_triggered`, `log_created`, `critical_file_deleted` |
| `agent-memory-poisoning` | `66666666-6666-6666-6666-666666666666` | `66666666-6666-6666-6666-aaaaaaaaaaa3` | `33333333-3333-3333-3333-333333333333` | `malicious_vendor_memory_written`, `poisoned_memory_retrieved_for_invoice`, `payment_routed_to_attacker_account` |

The runtime config aliases preserve compatibility with the original lab
configuration modules; they are not lab-version IDs. Historical Alembic
migrations remain self-contained snapshots. Learner-facing scenario content
lives in the frontend lab guide and runtime lab configs, while control-plane
scenario enforcement is isolated in `session_stream/lab_policy.py`.

### WebSocket deployment scope

The control plane's WebSocket connection registry is process-local. A
single-replica deployment can broadcast directly to every connection for a
session. Multiple replicas require sticky routing plus cross-replica fan-out
(for example Redis Pub/Sub) before a worker on one replica can reliably reach
connections owned by another.

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
runtimes/
  agent/             Per-session agent runtime — LLM loop, tool dispatch, lab configs
deploy/              Environment examples and Kubernetes deployment manifests
scripts/             Local smoke tests and operational utilities
```

Files under `deploy/` are operator examples. Replace reserved example domains,
container repositories, image digests, certificate contacts, and secret
references before using them in an environment.

## Getting Started

### Prerequisites

- Python 3.12+
- Node.js 22.22+
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
   # Edit .env with DATABASE_URL and the settings needed by the component
   # you are running.
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
   uv run uvicorn apps.control_plane.src.interfaces.http.main:app \
     --env-file .env --host 0.0.0.0 --port 8000 --reload
   ```

6. **Start the frontend** (separate terminal):
   ```bash
   cd apps/frontend
   cp .env.example .env.local
   # Set VITE_API_BASE_URL=http://localhost:8000 in .env.local.
   npm ci
   npm run dev
   ```

This starts the database, API, and frontend for component development. Running
a complete lab also requires a Kubernetes cluster: the provisioning worker
creates an isolated Pod and Service for every session. Configure the manifests
under `deploy/k8s/` with your own image references, secrets, ingress, and
OpenRouter test credentials before applying them. The checked-in deployment
files are operator examples, not a turnkey production environment.

To run an agent runtime directly for runtime-only development, provide the
session identity and model settings in `.env`, then use:

```bash
uv run uvicorn runtimes.agent.main:app \
  --env-file .env --host 0.0.0.0 --port 8001
```

The evaluator worker can be run against the local database in another terminal:

```bash
set -a
source .env
set +a
uv run python -m apps.evaluator.src.interfaces.runtime.evaluator_worker
```

### Full Kubernetes deployment

The repository includes Kustomize bases and environment overlays:

```bash
kubectl kustomize deploy/k8s/base
kubectl kustomize deploy/k8s/dev
```

Review every rendered resource before applying it. At minimum, replace image
references and digests, configure the required Kubernetes Secrets, and update
the example domains and certificate contacts. The helper scripts under
`scripts/` can bootstrap secrets and verify a configured cluster:

```bash
scripts/bootstrap_k8s_secrets_from_env.sh
scripts/verify_k8s_deploy.sh
```

After deployment, `scripts/smoke_session_roundtrip.sh` exercises a complete
session lifecycle.

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
- Production frontend build
- Backend: Ruff, mypy, Pyright, pytest
- Kubernetes manifest rendering for all included overlays
- Control-plane and agent-runtime container builds and import smoke checks

## License

Licensed under the [Apache License 2.0](./LICENSE).

The license covers the software and documentation, but it does not grant rights to use the Agent Failure name or branding except as described in [TRADEMARKS.md](./TRADEMARKS.md).

## Contributing

Contributions are welcome. Read [CONTRIBUTING.md](./CONTRIBUTING.md) before opening an issue or pull request. Participation is governed by the [Code of Conduct](./CODE_OF_CONDUCT.md).

Please report security vulnerabilities privately as described in [SECURITY.md](./SECURITY.md).
