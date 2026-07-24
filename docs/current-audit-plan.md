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

- [ ] Make broadcast delivery concurrent and failure-isolated.
- [ ] Ensure one failed connection cannot prevent delivery to healthy
  connections.
- [ ] Remove failed sockets from the session connection registry.
- [ ] Add tests with multiple clients, including one client that raises during
  delivery.
- [ ] Document that the in-memory connection registry is single-replica unless
  a cross-replica fan-out mechanism is introduced.

### Worker loops

- [ ] Prevent a learner-feedback processing exception from terminating its
  long-running worker.
- [ ] Remove the evaluator worker's outer `except Exception: pass`.
- [ ] Ensure every continued failure is logged with worker and correlation
  context.
- [ ] Extract a small shared worker-loop helper if it materially removes the
  repeated polling, exception, correlation, and sleep structure.
- [ ] Preserve each worker's explicit processing function and durable outbox
  retry behavior.

### Pilot request correctness

- [ ] Decide whether duplicate requests are defined by email alone or by
  `(email, university)`.
- [ ] Make the repository query, port name, tests, and learner-facing message
  reflect the same definition.
- [ ] Evaluate whether rate-limit enforcement requires an atomic database or
  Redis-backed mechanism based on expected traffic and deployment topology.

### Lab identities and generic-layer policy

- [ ] Inventory production lab IDs, lab-version IDs, aliases, objective keys,
  and learner-facing scenario constants across all applications.
- [ ] Give identifiers names that distinguish lab identity from lab-version
  identity.
- [ ] Establish one authoritative definition or generated artifact where
  values cross Python and TypeScript boundaries.
- [ ] Remove inline UUID construction from generic agent logic.
- [ ] Move lab-specific objective and scenario policy out of generic HTTP
  mapping where practical.

## Phase 4: Focused consolidation

### Frontend configuration and APIs

- [ ] Add one typed frontend environment/configuration module.
- [ ] Read `VITE_API_BASE_URL` and related settings through that module.
- [ ] Remove duplicated localhost defaults from feature modules.
- [ ] Keep the same-origin Vercel pilot-request submission separate from the
  generated FastAPI client unless that endpoint is moved into FastAPI.
- [ ] Confirm all remaining user-input forms use React Hook Form and shared Zod
  schemas where doing so removes meaningful state or validation duplication.

### Evaluator contracts

- [ ] Replace hand-synchronized evaluator rule dictionaries with one
  authoritative typed rule definition.
- [ ] Derive bundle membership, evidence requirements, and reason-code lookups
  from that definition.
- [ ] Retain fail-closed coverage tests for missing or inconsistent rule
  metadata.

### Outbox and retry plumbing

- [ ] Compare the outbox consumers and extract common claim/parse/dispatch
  mechanics only where transaction semantics remain explicit.
- [ ] Keep the transactional outbox pattern and database-backed retry state.
- [ ] Consider `tenacity` only for bounded, in-process transient operations
  such as readiness checks.
- [ ] Do not replace durable outbox retries with an in-memory retry library.
- [ ] Avoid introducing Celery, Dramatiq, Debezium, Kafka, Redis, or Socket.IO
  unless deployment scale creates a concrete operational requirement.

### Styling

- [ ] Inventory remaining inline style objects, Tailwind utilities, and stale
  CSS variables.
- [ ] Delete orphaned styles.
- [ ] Consolidate repeated tone/style maps when it improves maintainability.
- [ ] Treat a complete visual-system rewrite as optional rather than a release
  requirement.

## Phase 5: Complete the CBM semantics

The current compatibility adapter finds an observation that is already
classified as safe or unsafe and then supplies a fixed satisfied or violated
outcome. This preserved behavior during the structural migration, but it
should not be the final constraint model.

- [ ] Characterize current output before changing constraint semantics.
- [ ] Define relevance as whether a constraint applies to the current typed
  solution state.
- [ ] Define satisfaction as a real predicate over that state.
- [ ] Preserve normalized evidence independently from satisfaction and
  pedagogical presentation.
- [ ] Replace compatibility-era constant satisfaction predicates
  incrementally.
- [ ] Preserve finding order, evidence indexes, reason codes, feedback policy,
  and rule-bundle provenance unless a deliberate behavior change is
  documented.
- [ ] Remove compatibility helpers once no registered rule depends on them.
- [ ] Update `evaluator-model.md` to describe the final semantics.

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
