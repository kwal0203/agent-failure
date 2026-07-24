# Current Audit Cleanup Plan

This plan records the actionable findings from the second-pass review in
[`audit-advice.md`](audit-advice.md). It distinguishes confirmed cleanup work
from recommendations that are stale, disproportionate, or unsuitable for this
project.

## Goals

- Remove conspicuously unfinished or accidental code.
- Make simulated lab behavior originate from authoritative runtime and trace
  data.
- Improve runtime and control-plane resilience without introducing unnecessary
  infrastructure.
- Finish the evaluator's transition from compatibility-oriented CBM rules to
  genuine state-based constraint evaluation.
- Preserve application-specific designs that remain defensible, including the
  transactional outbox, enrollment authorization, and deterministic evaluator.

## Phase 1: Runtime abstractions and obvious debris

This phase is bounded and should not intentionally alter lab behavior.

- [x] Remove the evaluator `TestClass` debug dataclass.
- [x] Delete unreferenced frontend files:
  - `apps/frontend/src/pages/public/HomePage.tsx`
  - `apps/frontend/src/App.css`
- [x] Remove obsolete commented-out contract definitions and imports.
- [x] Remove stale commented JSX and clearly remove or label nonfunctional UI
  controls.
- [x] Correct known spelling errors, including
  `_is_idempo_unique_violoation` and `cas use it`.
- [x] Reclassify routine runtime logs from `WARNING` to `INFO` or `DEBUG`.
- [x] Retain `WARNING` for genuine rejection, degraded behavior, and failure
  conditions.
- [x] Add authority-bulletin handling to the generic `AgentLabHooks`
  abstraction with a no-op default.
- [x] Remove the generic runtime's `isinstance(hooks, Lab2Hooks)` special case.
- [x] Move Lab 1 and Lab 3 mutable class-level session collections onto hook
  instances or into `EphemeralRuntimeSessionState`.
- [x] Update affected tests and run the complete quality gate.

## Phase 2: Authoritative simulated telemetry

The labs are simulations, so synthetic scenario data is legitimate. The
problem is that the frontend currently fabricates runtime telemetry and
presents it alongside persisted runtime signals.

- [x] Remove the timed `LAB2_TELEMETRY_FEED` generator from
  `useSessionData.ts`.
- [x] Define the Lab 2 scenario telemetry in the runtime or another
  server-authoritative lab component.
- [x] Emit the scenario signals as trace events with stable identifiers and
  timestamps.
- [x] Render telemetry from persisted trace data only.
- [x] Clearly describe the signals in the UI and documentation as simulated
  lab telemetry.
- [x] Preserve deterministic replay and prevent duplicate signals.
- [x] Add tests covering generation, persistence, hydration, ordering, and
  deduplication.

## Phase 3: Control-plane resilience and shared identities

### WebSocket broadcast

- [x] Make broadcast delivery concurrent and failure-isolated.
- [x] Ensure one failed connection cannot prevent delivery to healthy
  connections.
- [x] Remove failed sockets from the session connection registry.
- [x] Add tests with multiple clients, including one client that raises during
  delivery.
- [x] Document that the in-memory connection registry is single-replica unless
  a cross-replica fan-out mechanism is introduced.

### Worker loops

- [x] Prevent a learner-feedback processing exception from terminating its
  long-running worker.
- [x] Remove the evaluator worker's outer `except Exception: pass`.
- [x] Ensure every continued failure is logged with worker and correlation
  context.
- [x] Extract a small shared worker-loop helper if it materially removes the
  repeated polling, exception, correlation, and sleep structure.
- [x] Preserve each worker's explicit processing function and durable outbox
  retry behavior.

### Pilot request correctness

- [x] Decide whether duplicate requests are defined by email alone or by
  `(email, university)`.
- [x] Make the repository query, port name, tests, and learner-facing message
  reflect the same definition.
- [x] Evaluate whether rate-limit enforcement requires an atomic database or
  Redis-backed mechanism based on expected traffic and deployment topology.

Duplicate pilot requests are defined by normalized work email alone within the
seven-day window. The database counters remain a documented best-effort abuse
guard for the low-volume control-plane endpoint. The hosted lead form is a
separate Vercel function; if the control-plane endpoint becomes a
multi-replica public intake path, its limits must move to an atomic shared
token bucket or API-gateway rate limiter.

### Lab identities and generic-layer policy

- [x] Inventory production lab IDs, lab-version IDs, aliases, objective keys,
  and learner-facing scenario constants across all applications.
- [x] Give identifiers names that distinguish lab identity from lab-version
  identity.
- [x] Establish one authoritative definition or generated artifact where
  values cross Python and TypeScript boundaries.
- [x] Remove inline UUID construction from generic agent logic.
- [x] Move lab-specific objective and scenario policy out of generic HTTP
  mapping where practical.

## Phase 4: Focused consolidation

### Frontend configuration and APIs

- [x] Add one typed frontend environment/configuration module.
- [x] Read `VITE_API_BASE_URL` and related settings through that module.
- [x] Remove duplicated localhost defaults from feature modules.
- [x] Keep the same-origin Vercel pilot-request submission separate from the
  generated FastAPI client unless that endpoint is moved into FastAPI.
- [x] Confirm all remaining user-input forms use React Hook Form and shared Zod
  schemas where doing so removes meaningful state or validation duplication.

### Evaluator contracts

- [x] Replace hand-synchronized evaluator rule dictionaries with one
  authoritative typed rule definition.
- [x] Derive bundle membership, evidence requirements, and reason-code lookups
  from that definition.
- [x] Retain fail-closed coverage tests for missing or inconsistent rule
  metadata.

### Outbox and retry plumbing

- [x] Compare the outbox consumers and extract common claim/parse/dispatch
  mechanics only where transaction semantics remain explicit.
- [x] Keep the transactional outbox pattern and database-backed retry state.
- [x] Consider `tenacity` only for bounded, in-process transient operations
  such as readiness checks.
- [x] Do not replace durable outbox retries with an in-memory retry library.
- [x] Avoid introducing Celery, Dramatiq, Debezium, Kafka, Redis, or Socket.IO
  unless deployment scale creates a concrete operational requirement.

### Styling

- [x] Inventory remaining inline style objects, Tailwind utilities, and stale
  CSS variables.
- [x] Delete orphaned styles.
- [x] Consolidate repeated tone/style maps when it improves maintainability.
- [x] Treat a complete visual-system rewrite as optional rather than a release
  requirement.

Frontend environment access now goes through `src/config.ts`. The public pilot
lead mutation intentionally continues to post to the same-origin Vercel
function, while authenticated control-plane calls use the generated FastAPI
client. Login, signup, password reset, enrollment, and injected-email forms use
shared Zod schemas with React Hook Form. The prompt composer remains controlled
local state because it is a live WebSocket input with only empty-string
normalization; adding a form abstraction there would not remove validation or
request-state complexity.

The outbox adapters now share only SQL row claiming and lifecycle transitions.
Payload validation and application dispatch remain event-specific. Durable
retry counters and availability timestamps still live in PostgreSQL. Tenacity
was not added to readiness polling: that loop evaluates returned Kubernetes
state as well as exceptions and already has injected clock/sleep functions for
deterministic tests, so a decorator would obscure rather than simplify it.

The styling inventory found Tailwind as the active visual system plus remaining
inline styles concentrated in layout-dependent session sizing and older catalog
views. Orphaned purple-theme variables and an unused social-icon rule were
removed. Repeated session status tones now resolve to one typed Tailwind class
map. Converting every dynamic layout style or redesigning the older catalog is
explicitly outside the release-critical cleanup.

## Phase 5: Complete the CBM semantics

The V1 rule bundles now use dynamic satisfaction predicates over typed solution
states. Required safe observations satisfy obligations; observed unsafe
behavior violates prohibitions. The versioned pedagogical policy continues to
control which outcomes are learner-visible, preserving the existing public
finding contract.

- [x] Characterize current output before changing constraint semantics.
- [x] Define relevance as whether a constraint applies to the current typed
  solution state.
- [x] Define satisfaction as a real predicate over that state.
- [x] Preserve normalized evidence independently from satisfaction and
  pedagogical presentation.
- [x] Replace compatibility-era constant satisfaction predicates
  incrementally.
- [x] Preserve finding order, evidence indexes, reason codes, feedback policy,
  and rule-bundle provenance unless a deliberate behavior change is
  documented.
- [x] Remove compatibility helpers once no registered rule depends on them.
- [x] Update `evaluator-model.md` to describe the final semantics.

Existing order, evidence-contract, positive/negative-path, malformed-input, and
repeated-event tests characterize the learner-visible output. Additional
kernel tests assert that empty typed states now produce genuine satisfied or
violated assessments while presentation policy suppresses outcomes that V1
did not historically expose. The obsolete fixed-outcome compatibility module
has been removed.

## Recommendations not adopted as requirements

### Local development authentication

`LocalTokenVerifier` is not currently a production authentication fallback:
configuration fails closed outside `APP_ENV=dev`. Local authentication remains
useful for development.

Potential cleanup:

- Rename it to `DevelopmentTokenVerifier`.
- Replace the stale "temporary migration" docstring.
- Make its development-only boundary explicit in construction and tests.

Deleting local authentication is not required.

### Enrollment authorization

OIDC authorization-code-with-PKCE authenticates users; it does not replace
authorization to join a course. The current signed, expiring,
database-recorded one-time enrollment token is a defensible application
protocol.

Future work should focus on transactionality, replay protection, and clear
expiry behavior rather than replacing enrollment with PKCE.

### Infrastructure frameworks

The project does not currently justify adopting a distributed task framework
or change-data-capture stack solely to remove small worker loops. A shared
loop abstraction should be attempted before adding operational dependencies.

### Static lab configuration

Moving prompts, seed files, and tool lists from Python to YAML is optional.
Python remains appropriate when the configuration is typed, versioned, and
closely coupled to hook behavior. A split should be made only if it creates a
clear authoring or validation benefit.

## Completion criteria

Each phase should:

- Preserve or deliberately document changes to learner-visible behavior.
- Add regression tests for every corrected failure mode.
- Pass the full local quality gate.
- Pass the pull-request CI workflow.
- Update this checklist and relevant architecture documentation.

The plan is complete when all adopted checklist items are checked or explicitly
closed with a documented rationale.
