# Open-Source Release Audit Plan

Pre-release review of the `agent-failure` codebase. Covers actual embarrassments to fix before tagging a release, and optional library/SaaS swaps for hand-rolled components.

## Summary assessment

The code is **not amateurish** and is, by industry norms, above median. Evidence:

- DDD / ports-and-adapters per feature (`application/` `infrastructure/` `interfaces/` `domain/`), with `*Port` protocols and SQLAlchemy adapters.
- Transactional outbox with `FOR UPDATE SKIP LOCKED`, idempotency stores, and per-event workers.
- Typing throughout: mypy **and** Pyright on the backend; strict TypeScript + Zod + `openapi-typescript`-generated types on the frontend.
- ~95 backend test files and ~36 frontend test files; pre-commit, import-linter, pip-audit, npm audit, multiple linters in CI.
- The "custom" components (outbox, worker loops, correlation IDs, WS registry) are deliberate minimal-dependency choices, each documented with its tradeoff (e.g. `apps/control_plane/src/interfaces/http/session_manager.py:10-15`).

The "custom → library" swaps below are about reducing maintenance surface area, not fixing bad code.

## Must-fix before release

1. **`apps/control_plane/src/infrastructure/auth/local_token_verifier.py:42`** — hardcodes `@gatech.edu`, leaking the customer into source. The class docstring also says *"Temporary verifier used during auth migration."* Either delete the verifier entirely or neutralize the domain to `example.com`.
2. **`apps/agent_harness/src/application/session_loop/service.py`** is mostly `TODO(E3-T2)` / `TODO(E3-T3,E5-T4)` stubs and reads as half-built. Either finish it, remove it from the public tree, or add a clear "work in progress" note.
3. **`main.py` at repo root** is the default `uv init` scaffold (`print("Hello from agent-failure!")`). Delete it — it is the first file visitors open.
4. **README claims `docs/open-source-audit.md`** but only `docs/evaluator-model.md` exists. Fix or remove the link.
5. **Internal-ticket jargon** in TODOs (`E3-T2`, `E5-T4`, `MVP`, `eval-window`) is meaningless to outsiders and reads like leaked Jira. Sweep these before tagging.
6. The `local:<user>:<role>` bearer format accepts unsigned tokens and trusts the role claim. Confirm `apps/control_plane/src/interfaces/http/dependencies.py` only selects `LocalTokenVerifier` when `APP_ENV=dev`. Tests suggest it does; verify before release.

## Custom → industry-standard replacements

Each swap is optional. Library and SaaS options are both listed.

| Custom thing | Location | Library replacement | SaaS replacement |
|---|---|---|---|
| Cognito JWT verification hand-rolled | `apps/control_plane/src/infrastructure/auth/cognito_jwt_verifier.py` (199 lines) | `cognitojwt`, `fastapi-azure-auth` | Already on Cognito. Or Auth0 / Clerk. |
| HS256 enrollment JWT mints | `apps/control_plane/src/application/enrollment/service.py` | Keep PyJWT, or delegate to Cognito | — |
| `while True: sleep()` worker loops (9 workers) | `apps/control_plane/src/interfaces/runtime/worker_loop.py` | **Celery** + Redis/RabbitMQ, or **Temporal** for the orchestrated flows | SQS + Lambda, GCP Cloud Tasks |
| Transactional outbox + claim loop | `apps/control_plane/src/infrastructure/persistence/outbox*.py` | Celery/RabbitMQ obviates it; or `pgqueuer` | — |
| Hand-rolled retry/backoff in provisioning | `apps/control_plane/src/application/orchestrator/provisioning.py` (`_wait_until_ready`) | **`tenacity`** | — |
| Count-based admission/rate limit | `apps/control_plane/src/infrastructure/policy/admission_policy.py` | **`slowapi`** | Upstash Redis rate-limit, Cloudflare |
| Correlation-ID-via-`ContextVar` + stdlib logging | `apps/control_plane/src/application/common/observability.py` | **`structlog`** + **OpenTelemetry** | Datadog, Honeycomb, Grafana Cloud |
| Hand-built `V1Pod`/`V1Service` + Server-Side-Apply | `apps/control_plane/src/infrastructure/orchestrator/k8s_provisioner.py` (343 lines) | **Helm** chart, or a Python operator via `kopf` | — |
| Process-local WebSocket registry | `apps/control_plane/src/interfaces/http/session_manager.py` | **Redis Pub/Sub** or `centrifugo` (already noted in the code) | Ably, Pusher, PubNub |
| Frontend custom dropdown / click-outside | `apps/frontend/src/layout/AppShell.tsx:106-128` | **Radix UI** (`@radix-ui/react-dropdown-menu`), or **shadcn/ui** | — |
| Frontend inline `style={{}}` mixed with Tailwind | `apps/frontend/src/layout/AppShell.tsx:273-411` ("legacy header") | Tailwind only | — |
| Frontend native `Date` math scattered (~26 spots) | various; helper in `apps/frontend/src/pages/session/helpers.ts` | **`date-fns`** or **`dayjs`** | — |
| Frontend has no component library | throughout | **shadcn/ui** + Radix (matches existing Tailwind v4) | — |
| Raw `fetch()` outlier for pilot requests | `apps/frontend/src/auth/pilotRequests.ts` (`createPilotRequest`) | Use the existing `openapi-fetch` client | — |

## What not to change

- **Transactional outbox.** Correct pattern. Do not rip it out for Celery unless you actually want the operational burden of a broker.
- **Ephemeral in-memory runtime state** (`runtimes/agent/session_state.py`). Correct for the single-Pod-per-session isolation model documented in the README.
- **LLM classifier wrappers.** There is no standard library for "LLM-as-a-judge"; the existing wrappers are typed against Pydantic `response_format` correctly.

## Suggested release-prep order

1. Delete `main.py`; fix the `@gatech.edu` hardcode and the "temporary verifier" docstring claims.
2. Sweep `E3-T2` / `MVP` / `eval-window` jargon from TODOs.
3. Decide whether `apps/agent_harness/src/application/session_loop/service.py` ships or gets hidden.
4. Fix the dead `docs/open-source-audit.md` link in the README.
5. Confirm `LocalTokenVerifier` is unreachable outside `APP_ENV=dev`.
6. *Then* decide which library/SaaS swaps above are worth the diff — most are not blocking a release.

## Note on "SASS"

If "sass" meant the CSS preprocessor: irrelevant — the frontend is already on Tailwind v4. If it meant SaaS / managed services: see the right-hand column of the table above.
