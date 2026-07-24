# Open-Source Release Audit

Pre-release review of the Agent Failure codebase: which parts would be
embarrassing to publish, and where custom/hand-rolled code should be replaced
with industry-standard libraries.

## Honest framing first

Self-assessment aside, the bones of this project are **above average for a
commercial codebase**, not amateurish:

- Genuine hexagonal architecture (ports/adapters).
- A correct transactional-outbox with `SELECT … FOR UPDATE SKIP LOCKED`.
- Proper PyJWT/JWKS verification.
- Correct OpenAI SDK usage.
- Idempotency enforced at the DB constraint level.
- Fail-closed settings; K8s pods with real security contexts; digest-pinned images.
- React Query used idiomatically; Amplify auth (not hand-rolled JWT).
- Serious test coverage.

The genuinely embarrassing items cluster into a small number of areas. They are
prioritized below.

---

## TIER 1 — Genuinely embarrassing (fix before `git push`)

### 1. Client fabricates fake telemetry and presents it as real
`apps/frontend/src/pages/session/hooks/useSessionData.ts:22-266`

Hardcoded `LAB2_TELEMETRY_FEED` injected on a timer, shown to learners as
`ERROR: …` runtime signals. For a *security-trace-reading* training product,
faking the data client-side is the single worst look in the repo. Move it
server-side or behind an explicit `mode === "demo"` flag.

### 2. `LocalTokenVerifier` ships in production
`apps/control_plane/src/infrastructure/auth/local_token_verifier.py:20`
(wired at `interfaces/http/dependencies.py:321`)

`Bearer local:anyone:admin` authenticates as admin with no signature/expiry.
Its own docstring says *"Temporary verifier used during auth migration."*
Delete it; keep the test-only `_LocalTestTokenVerifier` in `tests/conftest.py`.

### 3. `TestClass` left in core application types
`apps/evaluator/src/application/types.py:184`

A debug dataclass committed to the module every evaluator file imports. Pure
"I forgot to clean up."

### 4. `logger.warning` used for routine trace logging across the whole runtime
`runtimes/agent/agent.py:128,150,165,175,190,200,223,247,257,320`,
`main.py:85,120,128,329,378,399,415,502`, and all of `lab_002_tool_misuse.py`
and `lab_003_memory_poisoning.py`.

Every normal turn/iteration emits WARNINGs. Any operator would see a wall of
warnings on a healthy turn. These are `logger.info`/`logger.debug`.
(`auth.py:22,29` use warning correctly — leave those.)

### 5. `isinstance(hooks, Lab2Hooks)` inside the *generic* agent loop
`runtimes/agent/main.py:386`

The generic runtime special-cases one concrete lab class to call
`apply_authority_bulletin`. This is the textbook "broken abstraction" smell.
Put the method on the `AgentLabHooks` protocol with a no-op default.

### 6. Class-level mutable session state
`lab_001_prompt_injection.py:39-40`, `lab_003_memory_poisoning.py:58-59`

`set[UUID]`/`dict[UUID, …]` as **class attributes** = global mutable state
across the whole long-lived process. Never GC'd when a session ends (leak),
contradicts the per-seed `hooks_factory()`, and not concurrency-safe. Move onto
the instance or into `EphemeralRuntimeSessionState`.

### 7. Dead/orphaned frontend code shipped as if live
- `HomePage.tsx` (214 lines, zero imports, different color scheme) — delete.
- `App.css` (184 lines of Vite template, not imported anywhere) — delete.
- `"Demo Learner"` bootstrap in `AppShell.tsx:16-20`; non-functional
  "Resources/Courses/Notifications/(soon) GitHub" buttons — remove or flag
  clearly.
- `DEMO_H1_STYLE`/`DEMO_H2_STYLE` exports, `STUB_LABS` catalog — gate behind a
  real demo flag.

### 8. Commented-out code in the *contracts* package
`apps/contracts/src/runtime_trace.py:60-96`

20+ lines of dead contract definitions in the one package whose entire job is
to be authoritative.

---

## TIER 2 — Sloppy/buggy (should fix)

- **`learner_feedback_worker.run_forever` lacks `except`** —
  `interfaces/runtime/learner_feedback_worker.py:55-64`. The only worker wired
  into the FastAPI lifespan; one exception kills it silently. Its 7 siblings
  all have the belt.
- **`exists_recent_duplicate` ignores its `university` arg** (`_ = university`)
  — `pilot_request_repository.py:43`. Documented as (email, university) dedup
  but only checks email. A bug masquerading as style.
- **Hardcoded placeholder UUIDs inline in logic** — `agent.py:284`
  (`UUID("5555…")`), `session_stream/constants.py:3-4`, scattered across 3
  apps. Same UUID means *different* things in different apps (`5555…` = a
  lab_version in the evaluator, lab2-alias in the runtime, lab2-id in control
  plane). Centralize into one `LabIdentity` module.
- **`evaluator_worker` swallows all exceptions silently** —
  `evaluator_worker.py:73` `except Exception: pass` (no log).
- **Magic strings/content in generic layers** — `session_mapper.py:51-126`
  hardcodes lab objective keys (`"lab1.token_disclosure_attempt"`) inside the
  HTTP mapper; `LAB2_AUTHORITY_SIGNER = "Morgan Hale"`.
- **Spelling** — `_is_idempo_unique_violoation`
  (`unit_of_work_create_session.py:27`), "cas use it" (`models.py:140`).
- **Stale commented imports** — `interfaces/http/dependencies.py:5,119`;
  commented JSX in `LoginPage.tsx:346-354`.

---

## TIER 3 — "Custom" code → industry-standard replacements

| Custom code | Replacement | Location |
|---|---|---|
| **Hand-rolled WebSocket manager** (one dead client breaks broadcast to all — `session_manager.py:38-40`) | `asyncio.gather(..., return_exceptions=True)` over `anyio` task group; or **python-socketio** for rooms; add **Redis Pub/Sub** / Postgres `LISTEN/NOTIFY` for multi-replica fan-out | `interfaces/http/session_manager.py` |
| **8 near-identical `run_forever` worker loops** with hand-rolled polling | **arq** / **dramatiq** / **Celery beat** (you already have async workers) — or one shared `worker_loop()` helper | `interfaces/runtime/*_worker.py`, `evaluator_worker.py` |
| **6 copy-paste outbox consumer classes** (95% identical, with subtle divergences proving no one owns it) | One generic class parameterized by `event_type` + `payload_parser`; for off-the-shelf, **Debezium** (WAL→Kafka) or `LISTEN/NOTIFY` to wake instead of 100ms polls | `infrastructure/persistence/outbox_*.py` |
| **Hand-rolled retry/backoff** (`_retry_or_fail`, `_wait_until_ready`) | **`tenacity`** | `orchestrator/cleanup.py:215`, `provisioning.py:300`, `runtime/client.py` |
| **Hand-rolled DB-counter rate limiting** (TOCTOU race) for pilot requests | **`slowapi`** (FastAPI) or Redis token bucket (`redis-cell`) | `pilot_requests/service.py:48-66` |
| **Custom one-time-token enrollment redemption** | OIDC **auth-code-with-PKCE** against Cognito (which is already used for instructors) | `enrollment/service.py:51-149` |
| **Custom idempotency-key string builders** | Defensible (app-specific) — keep, but consider SHA-256 of a canonical tuple for collision-safety | `contracts/src/idempotency.py`, evaluator idempotency |
| **`react-hook-form` + `zod` installed but used in 1 of 6 forms**; others hand-roll `useState` + inconsistent regex/no email validation | Standardize on `react-hook-form` + shared `zod` schemas (already there for `PilotRequestPage`) | `LoginPage`, `SignupPage`, `ForgotPasswordPage`, `EnrollmentPage`, `useSessionActions.ts:23` |
| **3 coexisting styling systems** (Tailwind + 99 inline `CSSProperties` + orphaned purple CSS vars) and duplicated "tone" RGBA objects | Consolidate on Tailwind utility-class maps; delete `ui.ts`/`helpers.ts` inline tone objects; reconcile `--accent` with the real lime theme | `AppShell.tsx`, `ui.ts:81-139`, `helpers.ts:10-65`, `index.css:9` |
| **Raw `fetch()` next to typed `openapi-fetch` client** | Use the existing typed `createControlPlaneClient` everywhere | `auth/pilotRequests.ts:13-30` |
| **`VITE_API_BASE_URL` default duplicated in 5 files** | One `config.ts` env module | `ui.ts:5`, `useSessionStream.ts:28`, `enrollment.ts:8`, etc. |
| **`contract.py` triple hand-synced dicts** needing 4 test files to stay consistent | Define each rule **once** as a dataclass/Enum carrying `{id, bundle, evidence_keys, reason_code}`; derive the lookups; or load from YAML | `evaluator/.../rules/contract.py` |
| **Static lab content (prompts, seed files, tool lists) mixed with hooks in `.py`** | Split `labs/<slug>/config.yaml` + `labs/<slug>/hooks.py` | `runtimes/agent/lab_configs/*.py` |

### Custom code that is *not* worth replacing

Despite looking bespoke, these are appropriately scoped — not reinventions of
Drools/Redux/etc.:

- The CBM evaluator kernel (`cbm.py`).
- The rule registry (`registry.py`).
- The session state machine (`state_machine.py` — only 8 states).
- The outbox *pattern* itself (the claim logic is correct).

**One caveat:** the CBM `relevance`/`satisfaction` two-phase split is currently
*theatrical* — `satisfaction` ignores its context and returns a sealed constant
(`cbm_compat.py:101`). Either use real satisfaction predicates or collapse to
one phase.

---

## Bottom line

This is not an "amateurish codebase" problem. It is a **cleanup problem**: ~6
Tier-1 items (fake telemetry, the `local:` admin token, `TestClass`, dead UI
files, WARNING-spam, the `isinstance` leak) that would take a day or two to
delete/fix and would make the repo presentable. The custom infra is mostly
defensible; the real library wins are **WebSocket broadcast hardening, one
shared worker/retry abstraction (arq/tenacity), and standardizing the frontend
on the `react-hook-form`+`zod`+Tailwind stack that is already half-adopted.**
