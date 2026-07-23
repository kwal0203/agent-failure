# Open-Source Release Codebase Audit

## Verdict

This is not an amateur codebase. It is an overextended commercial MVP with
some genuinely solid engineering and several unfinished or hand-built areas.

I would be comfortable attaching my name to much of it after cleanup. I would
not publish the repository in its current state. The embarrassing part would
not be the general architecture—it would be releasing a security product with
exposed Git-history secrets, known dependency vulnerabilities, failing frontend
checks, and production-hardening TODOs.

No files were changed during this audit.

## Code I would clean up because it looks unfinished

### The report page

`apps/frontend/src/pages/SessionReportPage.tsx:1` is 897 lines and currently
combines:

- API fetching
- Persistence and hydration
- Autosave
- Navigation guards
- Evidence selection
- Report editing
- PDF generation
- Essentially all visual rendering

The most conspicuously homemade code is
`apps/frontend/src/pages/SessionReportPage.tsx:55`, which manually writes PDF
objects, byte offsets, cross-reference tables, and text commands. This is
exactly the sort of thing reviewers will question.

Replace it with
[`@react-pdf/renderer`](https://react-pdf.org/), which is designed to render
PDFs from React in browsers or servers. Split the page into report data hooks,
editor components, evidence components, and export rendering.

### The orchestrator service

`apps/control_plane/src/application/orchestrator/service.py:142` is 1,080
lines. Complexity analysis rated `process_pending_once` at 30 and `cleanup` at
26. It also contains visible scaffolding:

- Hard-coded retry and timeout constants
- A `retried_count` marked "not yet implemented"
- An empty-string `base_url` used to satisfy a non-null constraint
- Deferred duplicate-runtime keeper selection
- Deferred idle expiry
- A misspelled lab-difficulty parameter

The domain logic is legitimate, but split each state transition into a small
handler and make retry policy and configuration explicit.

Do not automatically replace the transactional outbox. That is an
industry-standard pattern and appears intentionally tested. Consider
Dramatiq, Celery, or Temporal only if operating the homegrown worker fleet is
more burden than value.

### Runtime state

`runtimes/agent/main.py:264` stores files, invoices, session transcripts,
inboxes, and seeded-session state in process-global memory.

Because the design provisions one runtime per session, this is more defensible
than it first appears. Still:

- Restarts erase state.
- Concurrent turns can mutate shared lists without locking.
- The module cannot safely scale to multiple workers.
- Old session dictionaries are never cleaned up within a long-lived process.

Either document "one process, one session, ephemeral by design" as an invariant
or give the runtime an explicit session-state abstraction backed by SQLite,
PostgreSQL, or Redis.

### Lab catalog validation

`apps/control_plane/src/infrastructure/persistence/lab_repository.py:23`
hardcodes the catalog, and `validate_lab()` returns `True` for every UUID. That
looks particularly unfinished because there are already lab tables and
active-version queries in the same repository.

Finish the database-backed catalog or clearly label this adapter as a demo
implementation.

### Evaluator rules

The evaluator files are large—Lab 1 exceeds 1,200 lines—and contain many regex
heuristics and repeated event-search logic.

This is custom domain logic, so replacing it wholesale with a framework would
probably make the code worse. Keep the evaluator, but:

- Extract repeated predicates and event indexes.
- Represent simple rules declaratively as data.
- Separate evidence extraction from instructional message construction.
- Document why deterministic rules are preferable to LLM-as-judge for these
  labs.
- Mark incomplete rules explicitly rather than leaving multiple "need endpoint
  before completed" TODOs inside a supposedly V1 bundle.

This is specialized, not embarrassing.

## Good library replacements

| Current custom code | Recommended replacement | Priority |
| --- | --- | --- |
| Manual environment parsing in `settings.py` | [`pydantic-settings`](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) with environment-aware validators | High |
| `kubectl` subprocesses and untyped manifest dictionaries | [Official Kubernetes Python client](https://github.com/kubernetes-client/python) or [`kubernetes-asyncio`](https://github.com/tomplus/kubernetes_asyncio) | High |
| Manual PDF object generation | [`@react-pdf/renderer`](https://react-pdf.org/) | High |
| Scattered fetch, loading, error, and autosave state | [TanStack Query](https://tanstack.com/query/latest/docs/framework/react/guides/queries) for queries and mutations | Medium |
| Raw Cognito HTTP calls and homegrown token-refresh lifecycle | AWS Amplify Auth, Cognito managed login, or a standard OIDC client | High |
| Handwritten REST response assertions and casts | Generate a client from FastAPI OpenAPI using [Orval](https://orval.dev/) or [`openapi-typescript`](https://openapi-ts.dev/) with `openapi-fetch` | Medium |
| Manual form parsing and validation | React Hook Form and Zod on the frontend; Zod in the Vercel function | Medium |
| Repeated raw OpenRouter HTTP and JSON extraction | An OpenAI-compatible SDK plus provider structured-output or JSON Schema support; retain Pydantic validation | Medium |
| Manual WebSocket lifecycle | `react-use-websocket` if reconnect, backoff, or heartbeat requirements grow | Low |
| Custom JWT/JWKS cache | PyJWT's `PyJWKClient`, Authlib, or OIDC middleware | Medium |

The current WebSocket protocol, evaluator rules, idempotency builders, state
machine, trace schema, and transactional outbox are project-specific enough
that I would not replace them merely to add fashionable dependencies.

## Repository presentation problems

These are easy to fix but make the repository look abandoned:

- `pyproject.toml:4` says `Add your description here`.
- `README.md:40` lists a nonexistent `infra/` directory and nonexistent
  `deploy/vps/`.
- Three documented `packages/` directories are empty.
- There are 77 documentation files, including 21 internal execution-plan
  files.
- Six staging release-record JSON files and two 6,437-line generated Flux
  manifests are committed.
- The README presents several planned directories as architecture.
- Production deployment files hardcode your GitHub username and personal
  email.
- Documentation references `status.agentfailure.com` and
  `api.agentfailure.com`; neither currently resolves, while the main site does.
- The frontend package is still named `frontend` at version `0.0.0`.
- The root contains both a polished public README and large amounts of private
  commercial planning history.

For the public repository, I would retain:

- Architecture and design rationale
- Lab specifications
- Instructor pack
- Public deployment examples
- ADRs explaining the evaluator, outbox, and runtime model

I would remove or move to an archive branch:

- Old execution plans and ticket dumps
- Generated Flux controller manifests
- Staging release records
- Empty planned packages
- Commercial viability and internal cleanup notes
- Production-specific account names, personal emails, domains, and image
  digests

## What is already strong

These parts will reflect well on you:

- Clear domain/application/infrastructure separation.
- Ports and adapters around runtime, persistence, auth, and orchestration.
- Typed Pydantic contracts shared with TypeScript.
- Extensive idempotency handling and transactional outbox usage.
- Explicit session lifecycle state machine.
- Strong database test safety: tests refuse to run against a database whose
  name does not contain `test`.
- Roughly 590 backend test functions plus 54 frontend tests.
- Mypy and Pyright both clean.
- Many meaningful negative-path and replay tests.
- Non-root containers, dropped capabilities, read-only filesystem support,
  resource limits, and disabled service-account token mounting.
- Good specifications and unusually thorough educational content.

My honest categorization is:

- About 70%: respectable and worth publishing.
- About 20%: normal MVP debt that should be labeled or tidied.
- About 10%: release blockers that would attract justified criticism.

Fix the secrets and history, auth behavior, dependency advisories, CI
omissions, Kubernetes cleanup, licensing, and public-facing repository
curation. After that, this becomes an interesting open-source security lab—not
an embarrassing failed project.
