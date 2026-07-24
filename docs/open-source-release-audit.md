# Open-Source Release Codebase Audit

## Current status

This audit originally described the repository before its open-source cleanup.
As of July 24, 2026, the release-blocking findings and the general-purpose
library replacements have been completed. The remaining substantive
maintainability project is the evaluator-rule cleanup described below.

| Area | Status |
| --- | --- |
| Report page decomposition and PDF generation | Completed |
| Orchestrator lifecycle service | Completed |
| Runtime state isolation | Completed |
| Database-backed lab catalog | Completed |
| Evaluator-rule organization | Completed |
| General-purpose library replacements | Completed |
| Repository presentation cleanup | Completed |

The original findings are retained below as a record of what was reviewed and
why the changes were made.

## Original verdict

This is not an amateur codebase. It is an overextended commercial MVP with
some genuinely solid engineering and several unfinished or hand-built areas.

I would be comfortable attaching my name to much of it after cleanup. I would
not publish the repository in its current state. The embarrassing part would
not be the general architecture—it would be releasing a security product with
exposed Git-history secrets, known dependency vulnerabilities, failing frontend
checks, and production-hardening TODOs.

No files were changed during the original audit.

## Code I would clean up because it looks unfinished

### The report page

**Status: Completed.** The page has been split into focused report hooks and
components, persisted data uses shared query infrastructure, autosave has
explicit draft safety, and PDF generation uses `@react-pdf/renderer`.

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

**Status: Completed.** Provisioning, cleanup, reconciliation, expiry, trace,
and policy handling now live in focused modules. Retry and timeout policy is
validated configuration, runtime URLs have explicit pending semantics,
duplicate-runtime selection is deterministic, and database heartbeats were
removed.

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

**Status: Completed.** Mutable runtime data is owned by an explicit
`EphemeralRuntimeSessionState`. Kubernetes supplies the owning session UUID,
cross-session requests fail closed, turns are serialized, tool mutations are
lock-protected, and shutdown clears the state. The intentionally ephemeral
one-Pod-per-session lifecycle is documented in the README.

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

**Status: Completed.** The catalog and validation paths now query active,
published labs and active lab versions from PostgreSQL.

`apps/control_plane/src/infrastructure/persistence/lab_repository.py:23`
hardcodes the catalog, and `validate_lab()` returns `True` for every UUID. That
looks particularly unfinished because there are already lab tables and
active-version queries in the same repository.

Finish the database-backed catalog or clearly label this adapter as a demo
implementation.

### Evaluator rules

**Status: In progress.** The first cleanup phase removed the unfinished
Easy/Medium/Hard dimension across the UI, API, persistence, runtime, and
evaluator. The former Medium behavior is now the single canonical lab model.
Evaluator bundles resolve only by lab slug and lab version; unknown lab bundles
fail closed. The registry, rather than a caller or queued task, owns each
bundle's `rule_bundle_version`. That version is retained on evaluation results,
idempotency keys, logs, and evaluator-authored objective events as scoring-rule
provenance. Characterization tests preserve the canonical rule ordering,
evidence, feedback, and objective behavior before the structural CBM refactor
begins.

The second cleanup phase added one immutable, order-preserving trace index per
evaluation and explicit solution-state types for Prompt Injection, Tool Misuse,
Code Execution, and Memory Poisoning. Each rule bundle owns the function that
derives its state from the trace. Existing rule output remains unchanged through
an ordered-event compatibility view; the typed states are the input foundation
for the subsequent CBM-kernel and incremental rule-migration phases.

The third cleanup phase introduced a small constraint-based modeling kernel.
Constraints now have separate, explicit relevance and satisfaction conditions;
irrelevant constraints do not evaluate satisfaction, and inconsistent result
states fail closed. Constraint evidence records trace positions and normalized
facts without containing feedback policy. A temporary compatibility adapter can
project satisfied or violated constraints into the existing evaluator finding
contract, preserving current persistence and API behavior while individual lab
rules migrate.

The fourth cleanup phase migrated Code Execution, Tool Misuse, and Memory
Poisoning onto that kernel. Their constraints consume typed solution states,
emit normalized evidence, and explicitly classify observed safe behavior as
satisfied and unsafe behavior as violated. The compatibility adapter preserves
the established finding order, codes, reason codes, feedback levels, evidence
indexes, and payloads. Structural tests prevent these bundles from drifting back
to handwritten finding functions.

The fifth cleanup phase separated assessment from pedagogical presentation.
The migrated lab modules now contain only constraint semantics and evidence
extraction. A versioned pedagogical-policy catalog independently decides which
satisfied or violated outcomes are learner-visible and maps them to the current
result type, feedback level, and reason code. The existing feedback catalog then
selects learner-facing text from that reason code. Policy coverage tests fail
closed if a migrated constraint has no mapping and ensure the catalog covers
exactly the migrated rule set.

The original evaluator files were large—Prompt Injection was roughly 900
lines—and contained many regex heuristics and repeated event-search logic.

This is custom domain logic, so replacing it wholesale with a framework would
probably make the code worse. Keep the evaluator, but:

- Migrate repeated predicates and trace searches onto the shared indexed state.
- Represent simple rules declaratively as data.
- Separate evidence extraction from instructional message construction.
- Document why deterministic rules are preferable to LLM-as-judge for these
  labs.
- Mark incomplete rules explicitly rather than leaving multiple "need endpoint
  before completed" TODOs inside a supposedly V1 bundle.

The sixth cleanup phase migrated Prompt Injection onto the same CBM kernel and
split its implementation into focused pattern, evidence, and bundle modules.
All registered lab bundles now use typed solution states and CBM constraints.
The versioned pedagogical policy covers the complete constraint catalog, while
the compatibility import preserves existing module consumers. The evaluator's
deterministic assessment model, rule-bundle versioning, fail-closed boundaries,
and deliberately limited use of LLM classification are documented in
[`evaluator-model.md`](evaluator-model.md).

This is specialized, not embarrassing.

## Good library replacements

**Status: Completed.**

| Original custom code | Implemented replacement | Priority |
| --- | --- | --- |
| Manual environment parsing in `settings.py` | `pydantic-settings` with environment-aware validators | High |
| `kubectl` subprocesses and untyped manifest dictionaries | Official Kubernetes Python client | High |
| Manual PDF object generation | `@react-pdf/renderer` | High |
| Scattered fetch, loading, error, and autosave state | TanStack Query queries and mutations | Medium |
| Raw Cognito HTTP calls and homegrown token-refresh lifecycle | AWS Amplify Auth | High |
| Handwritten REST response assertions and casts | Generated OpenAPI TypeScript client | Medium |
| Manual form parsing and validation | React Hook Form and Zod | Medium |
| Repeated raw OpenRouter HTTP and JSON extraction | OpenAI-compatible SDK with schema-constrained output and Pydantic validation | Medium |
| Manual WebSocket lifecycle | `react-use-websocket` | Low |
| Custom JWT/JWKS cache | PyJWT `PyJWKClient` | Medium |

The current WebSocket protocol, evaluator rules, idempotency builders, state
machine, trace schema, and transactional outbox are project-specific enough
that I would not replace them merely to add fashionable dependencies.

## Repository presentation problems

**Status: Completed.** The README and package metadata were corrected,
obsolete deployment and generated release artifacts were removed, and the
documentation directory was curated to retain this audit and the instructor
pack. The findings below describe the original repository.

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

The original categorization was:

- About 70%: respectable and worth publishing.
- About 20%: normal MVP debt that should be labeled or tidied.
- About 10%: release blockers that would attract justified criticism.

The secrets and history, auth behavior, dependency advisories, CI omissions,
Kubernetes cleanup, licensing, and public-facing repository curation have now
been addressed. The repository is suitable for an open-source security lab;
the remaining evaluator work is maintainability cleanup rather than a release
blocker.
