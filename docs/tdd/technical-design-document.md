# Technical Design Document

## Context and overview

This Technical Design Document specifies the production architecture for a public AI agent security lab platform in which learners interact with instrumented labs that exercise prompt injection, retrieval misuse, unsafe tool use, constrained file operations, and defense-oriented agent behavior inside isolated execution environments. It defines how the platform delivers low-latency learner interaction, strict session isolation, structured trace capture, versioned constraint-based evaluation, and production-grade operational controls.

The platform consists of a React-based learner interface, a Control Plane API, an Orchestrator responsible for lab container lifecycle, an Agent Harness that mediates model calls and tool execution inside each lab container, and an asynchronous evaluation pipeline that turns traces and environment telemetry into instructional feedback. The design assumes public deployment, adversarial usage, and dependence on an external LLM gateway such as OpenRouter. Accordingly, the architecture prioritizes containment, auditability, recoverability, and cost control alongside instructional usefulness.

This document explains how the system satisfies the PRD requirements around lab lifecycle, role-based access, artifact handling, traceability, abuse prevention, observability, and public-production readiness. fileciteturn1file0

## Goals, constraints and non-goals

### Goals

- **Lab isolation and containment**: Execute every learner run in a fresh lab container with strict isolation from other learners and from the platform control plane.  
- **Instructionally meaningful traces**: Capture prompts, model outputs, tool calls, tool outputs, policy denials, and relevant environment state transitions as structured trace events tied to a single session.  
- **Constraint-based feedback**: Support lab-specific success signals, constraint violations, and tiered feedback derived from observable system behavior rather than only free-form textual judgments.  
- **Responsive learner experience**: Deliver low-latency streaming interaction and near-real-time trace visibility suitable for an interactive lab experience.  
- **Production operational safety**: Support authentication, role-based authorization, quotas, auditability, backup/restore, degraded-mode operation, and emergency controls required for public deployment.  
- **Reproducibility and versioning**: Version lab definitions, tool contracts, prompts, and evaluation logic so historical runs remain interpretable.

### Constraints

- **Time and delivery budget**: The initial implementation is time-constrained and should prefer managed services for identity, cloud databases, and secrets management rather than custom infrastructure where possible.  
- **Core stack**: The system should use a React frontend, an asynchronous backend suitable for streaming and concurrent session management, and PostgreSQL as the primary durable store.  
- **External model dependency**: All model inference is routed through OpenRouter or an equivalent hosted provider. The system must tolerate provider outages, latency spikes, and quota limits.  
- **Public deployment threat model**: The design must assume automated abuse, repeated probing of isolation boundaries, and attempts to trigger excessive spend.  
- **Environment separation**: Development, staging, and production must be separated, and lower environments must not depend on unrestricted access to production data or production secrets.

### Non-goals

- **Multi-region active-active deployment** for the initial release.  
- **Local hosting or fine-tuning of open-weight models** inside the platform cluster.  
- **Fully automated generation of constraint logic** from lab traces.  
- **Enterprise organization management** beyond the minimal access roles required for the first public release.  
- **A general-purpose coding environment** outside the scope of defined lab contracts. fileciteturn1file0

## System architecture

The system is organized around a clear split between the public-facing control plane and the untrusted per-session execution plane.

### 1\. Learner Interface

**Technologies**: React, browser-based state management, secure WebSocket client, static asset hosting.

**Responsibilities**:

- Present the lab catalog, learner session history, trace viewer, and lab interaction interface.  
- Stream learner prompts and render model output, tool traces, constraint feedback, and session state changes in real time.  
- Support authenticated session resume, and clear messaging for policy denials, quota errors, and environment failures.

The learner interface is not a source of truth for session state. It is a rendering and interaction layer backed by the Control Plane.

### 2\. Control Plane API

**Technologies**: FastAPI or Go, managed identity provider integration, PostgreSQL access layer, internal event bus, WebSocket session manager.

**Responsibilities**:

- Authenticate incoming requests and enforce role-based authorization.  
- Own session creation, session status transitions, resume eligibility, and learner-visible history.  
- Expose REST endpoints for lab launch, session metadata, lab metadata, and administrative actions.  
- Maintain persistent WebSocket connections for active sessions and multiplex model output, trace events, and tutor feedback back to the learner interface.  
- Persist durable session records, chat records, trace events, audit logs, quota state, and evaluation records.  
- Enforce rate limits, quotas, concurrency restrictions, and high-level policy denials before forwarding work to a lab container.

The Control Plane is the system-of-record boundary for durable product state.

### 3\. Orchestrator

**Technologies**: Kubernetes, cluster API client, image registry, namespace and policy management.

**Responsibilities**:

- Provision a fresh lab container for each learner session from the selected lab definition.  
- Apply lab-specific runtime configuration, resource limits, network policy, mounted artifacts, and environment variables.  
- Track provisioning, readiness, health, and termination status for active lab sessions.  
- Ensure failed or expired sessions are cleaned up and associated transient state is removed.  
- Support administrative controls such as disabling new launches for a lab or globally halting new session creation during an incident.

The Orchestrator must never grant the lab container direct access to the database, secret store, or internal administrative services.

### 4\. Agent Harness

**Technologies**: Python runtime inside each lab container, lab-specific tools, streaming HTTP/WebSocket client to the model gateway.

**Responsibilities**:

- Translate learner prompts and session context into model requests.  
- Intercept tool call intents from the model and execute only those tools allowed by the active lab contract.  
- Apply tool-level policy checks and generate structured policy-denial events for disallowed actions.  
- Capture tool outputs, environment state changes, and relevant runtime telemetry.  
- Stream structured events back to the Control Plane in session order.

The Agent Harness is the only code inside the lab container that interacts with the model gateway and local lab tools. It operates under least privilege and inside the same isolation boundary as the rest of the lab runtime.

### 5\. Constraint Evaluation Pipeline

**Technologies**: asynchronous worker service, PostgreSQL polling or queue consumption, internal pub/sub for feedback delivery.

**Responsibilities**:

- Consume committed trace events from active or completed sessions.  
- Load the versioned evaluation logic and constraint set associated with the lab definition used in the run.  
- Determine whether recent trace events imply success, partial success, policy violations, unsafe behavior, or feedback-worthy state transitions.  
- Persist evaluation outcomes separately from raw traces.  
- Publish learner-visible tutor feedback events and operator-visible quality signals without blocking the main interaction path.

This pipeline must be decoupled from the critical path so delayed evaluation cannot stall model interaction. fileciteturn1file0

## Request flows

### 1\. Lab launch flow

1. The learner selects a lab from the lab catalog.  
2. The learner interface submits a `POST /api/v1/sessions` request with the `lab_id` and an idempotency key.  
3. The Control Plane verifies authentication, authorizes the learner for the requested lab, checks quota and abuse controls, and creates a durable session record with status `PROVISIONING`.  
4. The Control Plane loads the current published lab definition, including the lab image, tool contract, resource limits, and evaluation version.  
5. The Control Plane requests the Orchestrator to provision a fresh lab container.  
6. When the lab container passes readiness checks, the Orchestrator reports readiness to the Control Plane.  
7. The Control Plane marks the session `ACTIVE`, records launch telemetry, and returns session metadata to the learner interface.  
8. The learner interface opens the session WebSocket and begins streaming interaction.

### 2\. Learner interaction flow

1. The learner submits a prompt or permitted artifact via the session UI.  
2. The Control Plane validates session ownership, session status, per-session concurrency rules, and quotas.  
3. The Control Plane records the learner input as durable session state and appends a trace event.  
4. The Control Plane forwards the learner input to the Agent Harness for the active lab session.  
5. The Agent Harness calls the model gateway and streams model output back toward the Control Plane.  
6. If the model emits a tool call, the Agent Harness validates it against the active tool contract and either executes it locally or emits a policy-denial event.  
7. The Agent Harness streams model chunks, tool events, policy decisions, and relevant environment telemetry back to the Control Plane.  
8. The Control Plane persists the stream as structured trace records and multiplexes learner-visible events down the WebSocket.

### 3\. Constraint-feedback flow

1. Newly committed trace events become visible to the evaluation pipeline.  
2. An evaluator loads the lab definition version and associated constraint set for the session.  
3. The evaluator determines whether recent activity triggered a constraint violation, success milestone, hint threshold, or no-op result.  
4. The evaluator persists the evaluation result and any associated feedback payload.  
5. If learner-visible feedback should be delivered immediately, the evaluator publishes it to the Control Plane.  
6. The Control Plane injects the tutor feedback into the active WebSocket stream or stores it for later retrieval if the learner is offline.

### 4\. Resume flow

1. The learner returns to an existing session page.  
2. The learner interface requests session metadata, history, and resume state.  
3. The Control Plane determines whether the session is resumable according to the lab’s lifecycle policy.  
4. If the session is still active, the learner reconnects to the existing session stream.  
5. If the session requires reconstruction, the Control Plane uses persisted session artifacts, chat state, and lab definition metadata to recreate the allowed resume state and bring up a fresh lab container if supported.  
6. If the session is not resumable, the learner is offered a fresh launch instead.

### 5\. Administrative control flow

1. An authorized operator performs an action such as viewing a failed session, suspending a user, disabling a lab, or entering degraded mode.  
2. The Control Plane verifies the operator’s role and the specific permission required.  
3. The action is written to the audit log and, if applicable, propagated to the Orchestrator or enforcement subsystems.  
4. The system applies the requested control and returns confirmation to the operator interface.

## Data model and schema

PostgreSQL is the durable source of truth for user identity linkage, session state, trace records, lab metadata, evaluation outputs, quota state, and audit history. The schema is relational-first, with JSONB used for flexible event payloads and versioned lab metadata.

### Core relational models

**users**

- `id` (UUID, primary key)  
- `identity_provider_subject` (VARCHAR, unique)  
- `email` (VARCHAR, unique)  
- `role` (ENUM: learner, admin, optional future roles)  
- `status` (ENUM: active, suspended, deleted)  
- `created_at`, `updated_at`

**labs**

- `id` (UUID, primary key)  
- `slug` (VARCHAR, unique)  
- `name` (VARCHAR)  
- `status` (ENUM: draft, published, disabled)  
- `current_version_id` (UUID, foreign key)  
- `created_at`, `updated_at`

**lab\_versions**

- `id` (UUID, primary key)  
- `lab_id` (UUID, foreign key)  
- `docker_image` (VARCHAR)  
- `tool_contract` (JSONB)  
- `constraint_bundle` (JSONB or foreign key reference)  
- `system_prompt_bundle` (JSONB)  
- `runtime_policy` (JSONB)  
- `published_at`

**sessions**

- `id` (UUID, primary key)  
- `user_id` (UUID, foreign key)  
- `lab_id` (UUID, foreign key)  
- `lab_version_id` (UUID, foreign key)  
- `status` (ENUM: provisioning, active, idle, completed, expired, failed)  
- `resume_policy` (ENUM or JSONB snapshot)  
- `idempotency_key` (VARCHAR, unique)  
- `container_id` or `pod_name` (VARCHAR)  
- `trace_root_id` (VARCHAR)  
- `started_at`, `ended_at`, `created_at`, `updated_at`

### Interaction and trace models

**chat\_messages**

- `id` (UUID, primary key)  
- `session_id` (UUID, foreign key)  
- `message_index` (BIGINT)  
- `role` (ENUM: user, assistant, system, tool)  
- `content` (TEXT)  
- `metadata` (JSONB)  
- `created_at`

**trace\_events**

- `id` (UUID, primary key)  
- `session_id` (UUID, foreign key, indexed)  
- `trace_root_id` (VARCHAR, indexed)  
- `event_index` (BIGINT)  
- `event_type` (VARCHAR)  
- `source` (ENUM: control\_plane, agent\_harness, evaluator, orchestrator)  
- `payload` (JSONB)  
- `created_at`

**evaluation\_results**

- `id` (UUID, primary key)  
- `session_id` (UUID, foreign key)  
- `trace_event_id` (UUID, nullable foreign key)  
- `constraint_id` (VARCHAR)  
- `result` (ENUM: pass, fail, partial, not\_applicable)  
- `feedback_level` (ENUM: none, flag, hint, detailed\_hint)  
- `feedback_payload` (JSONB)  
- `created_at`

### Operational and governance models

**quota\_counters**

- `id` (UUID, primary key)  
- `user_id` (UUID, foreign key)  
- `window_start` (TIMESTAMP)  
- `metric_type` (VARCHAR)  
- `value` (BIGINT)

**audit\_logs**

- `id` (UUID, primary key)  
- `actor_user_id` (UUID, nullable foreign key)  
- `action_type` (VARCHAR)  
- `target_type` (VARCHAR)  
- `target_id` (VARCHAR)  
- `payload` (JSONB)  
- `created_at`

Indexes should support session lookup, ordered replay, active session management, quota enforcement, and evaluator access to recent trace events. JSONB fields should be indexed selectively rather than universally to avoid write amplification. fileciteturn1file0

## Authorization model and permission matrix

The platform uses role-based access control enforced in the Control Plane. Authentication proves identity; authorization determines whether that identity may access a specific session, trace, lab-administration action, or operational workflow.

### Roles in the initial release

**Learner**

- Can browse published labs.  
- Can create and interact with their own sessions.  
- Can view their own trace history, and feedback as permitted by the lab contract.  
- Cannot view or modify other learners’ sessions, traces, quota state, or audit logs.  
- Cannot invoke administrative controls.

**Administrator**

- Can inspect any session, trace, runtime failure, and abuse signal for operational, moderation, or support purposes.  
- Can suspend users, disable labs, limit launches, and place the platform in degraded mode.  
- Can access audit views and operational dashboards.  
- Cannot bypass audit logging for privileged actions.

**Future instructor/researcher roles** These roles are intentionally deferred. The initial design should keep authorization extensible so narrower privileged roles can be added later without reworking the ownership model.

### Resource-level authorization rules

- Session access is owner-scoped unless an administrator is explicitly authorized.  
- Trace access is scoped to the session owner and administrators.  
- Administrative APIs require both an authenticated identity and an allowed administrative role.  
- Role changes, suspension actions, and lab-disable actions are privileged events that must be written to the audit log before confirmation is returned.

### Support-access principle

Administrative inspection exists for operational support, moderation, abuse handling, and debugging. The design assumes support access is exceptional rather than default and should be observable in audit records.

## API design and data contracts

The platform uses REST for durable resource and lifecycle operations and WebSockets for active session streaming.

### REST API

**POST `/api/v1/sessions`** Creates a new lab session.

- Requires bearer authentication.  
- Requires `Idempotency-Key` header.  
- Validates lab availability, learner authorization, and quota state.  
- Returns `202 Accepted` with session metadata when provisioning begins.

**GET `/api/v1/sessions/{session_id}`** Returns session metadata, resume status, and learner-visible history.

- Enforces ownership or administrative access.

**POST `/api/v1/admin/labs/{lab_id}/disable`** Administrative endpoint to disable launches for a lab.

- Requires admin role.  
- Writes an audit log.

### WebSocket protocol

**Connection**: `WSS /api/v1/sessions/{session_id}/stream`

Client-to-server message types include:

- `USER_PROMPT`  
- `SESSION_PING`

Server-to-client message types include:

- `AGENT_TEXT_CHUNK`  
- `TRACE_EVENT`  
- `TUTOR_FEEDBACK`  
- `SESSION_STATUS`  
- `POLICY_DENIAL`  
- `QUOTA_ERROR`  
- `SYSTEM_ERROR`

Message envelopes should include:

- `type`  
- `session_id`  
- `trace_root_id`  
- `event_id` or ordered sequence number where applicable  
- typed `payload`

The contract should guarantee ordered delivery within a session as observed by the Control Plane, while allowing evaluator-derived feedback to arrive asynchronously after the triggering trace event.

## Event transport and delivery semantics

The platform uses two distinct event paths: a durable path for correctness and replay, and a transient path for live UX.

### Durable event path

- The durable source of truth for trace events is PostgreSQL.  
- The Control Plane persists learner inputs and runtime events before or during delivery to downstream consumers according to the event type.  
- The evaluator consumes committed trace records only.  
- If a transient stream fails, durable session history remains recoverable from the database.

### Live streaming path

- The active session WebSocket is used for low-latency learner-visible updates.  
- WebSocket delivery is best-effort for live experience, but missed live events must be reconstructable from durable trace history.  
- Reconnect logic should request the latest acknowledged event index and replay any missed learner-visible events that are still relevant.

### Ordering guarantees

- Ordering is guaranteed within a single session as persisted by the Control Plane using a session-scoped monotonically increasing event index.  
- Cross-session global ordering is not required.  
- Evaluator feedback may appear after the trace event that triggered it, but the feedback payload must reference the triggering event or event range.

### Retry and failure handling

- Event producers retry transient failures with bounded backoff.  
- Evaluator workers must be able to resume from the last committed durable position without duplicating externally visible outcomes.  
- Duplicate evaluator attempts should be harmless through idempotent persistence keyed by session, constraint, and triggering event.  
- Poison events or repeatedly failing evaluation tasks should be surfaced to operators and isolated from the main interaction path.

### Implementation note

The first release may use PostgreSQL-backed durable consumption rather than introducing a separate queue. If traffic or evaluator lag later justifies a dedicated broker, the correctness contract above remains the source of truth.

## Consistency and correctness semantics

### Idempotent session creation

Lab launch is a high-latency and cost-bearing action. Every session-creation request must include an idempotency key. The session table enforces uniqueness on this key so retries return the existing session instead of provisioning duplicate lab containers.

### Single active learner turn per session

The platform must process learner prompts sequentially within a session. The Control Plane enforces per-session concurrency using a session lock or ordered work queue. A learner cannot create overlapping tool-execution cycles within the same lab run.

### Ordered trace append

Trace events from the Agent Harness and Control Plane must be appended in a stable session order using a monotonically increasing session-scoped index or equivalent ordering mechanism. The evaluator consumes only committed trace records.

### Session state reconciliation

The durable session record is authoritative for learner-visible state, but the Orchestrator and runtime health stream may detect that the actual lab container is missing, unhealthy, or terminated. A reconciliation loop must update session status if runtime state diverges from persisted expectations.

### Resume semantics

Resume behavior is lab-version specific and must be explicit rather than inferred.

- **Hot resume**: If the original lab container is still alive and the session remains resumable, the learner reconnects to the existing runtime and stream.  
- **Warm reconstruction**: If the original lab container is gone but the lab contract permits reconstruction, the Control Plane provisions a fresh lab container and restores only the persisted state allowed by the resume policy, such as learner-visible message history, and selected lab metadata.  
- **Cold restart only**: Some labs may intentionally disallow reconstruction because important ephemeral state cannot be restored safely or instructionally.

The session record must therefore capture the resume policy, whether reconstruction is supported, and which state classes are durable versus ephemeral. At minimum, the design distinguishes among:

- durable message history  
- durable evaluation results  
- ephemeral process memory inside the lab container  
- ephemeral filesystem state unless the lab explicitly snapshots it  
- ephemeral network or timing state

A learner must never be silently attached to the wrong reconstructed state. If resume is unavailable, the UI should say so explicitly and offer a fresh run.

### Version-stable evaluation

Every session must point to the exact lab version used to provision it. Evaluators must load the matching tool contract, prompt bundle, and constraint bundle rather than the newest published version.

### Auditability of privileged actions

Administrative state changes must be durable and auditable. Privileged actions that fail partway through should be surfaced clearly and must not silently produce ambiguous control state.

## Failure modes and resiliency

### Model gateway outage or rate limiting

If OpenRouter or the selected model path becomes unavailable, the Agent Harness emits a structured provider-failure event. The Control Plane surfaces a learner-visible degraded-state message and pauses interaction without losing durable session history.

### Lab container crash or forced termination

If a learner action or model-driven tool path crashes the lab container, the Orchestrator reports the termination and the Control Plane transitions the session to `FAILED` or another appropriate terminal state. The learner is informed and may be offered restart or resume options according to lab policy.

### Client disconnect during active session

A WebSocket disconnect must not lose session state. Because learner prompts and trace events are persisted as they occur, the learner can reconnect and resume from durable state when supported.

### Evaluation backlog

If the evaluation pipeline lags behind active sessions, learner interaction continues. Tutor feedback may arrive late, but it must not block the session. Backpressure thresholds and dead-letter handling should prevent silent evaluator loss.

### Provisioning timeout or partial launch

If a lab container never reaches readiness, the session must not remain indefinitely in `PROVISIONING`. The Control Plane should timeout, mark the session as failed, log the cause, and surface a retry path.

### Database or storage degradation

If PostgreSQL or artifact storage becomes unavailable, the platform should reject new launches and enter a safer degraded mode rather than allowing partial session persistence. Operator-visible alerts and recovery actions must be triggered.

## Data lifecycle, retention, and backup policy

The technical design must support the product-level retention and deletion policy with concrete data classes.

### Data classes

**System-of-record data**

- users  
- sessions  
- lab metadata and versions  
- evaluation records  
- quota counters  
- audit logs

**High-volume operational data**

- trace events  
- chat messages  
- runtime logs  
- metrics and health signals

### Lifecycle expectations

- User and session records remain durable according to product retention policy and legal needs.  
- Trace events may be retained for a shorter period than core session summaries if cost or privacy requires tiered retention.  
- Audit logs must be retained long enough to support operational investigation and privileged-action review.  
- Backup retention windows must be defined for critical stores and aligned with restore objectives.

### Backup objectives

- PostgreSQL backups must support point-in-time recovery where feasible.  
- Backup frequency and retention should be chosen to satisfy the product’s recovery point objective.  
- Restore tests must be run on a scheduled basis in a non-production environment.  
- Restore validation must verify not just database recovery, but application ability to read recovered session state.

## Service level objectives and operational targets

The first public release should define measurable targets so the design can be validated against them.

### Initial target SLOs

- **Session launch success rate**: at least 99% over a rolling 30-day window, excluding scheduled maintenance.  
- **p95 session provisioning latency**: 15 seconds or less for supported labs under expected load.  
- **p95 time to first model token**: 4 seconds or less after a learner prompt reaches the Agent Harness, excluding upstream provider-wide incidents.  
- **p95 tutor feedback latency**: 10 seconds or less for feedback paths that depend on asynchronous evaluation.  
- **Critical data restore success**: successful restore test for system-of-record data at least once per defined validation window.  
- **Administrative action audit coverage**: 100% of privileged actions recorded in the audit log.

### Error-budget framing

If the platform consumes its error budget for launch success or availability, operators should be able to slow rollout, disable unstable labs, or enter degraded mode until reliability recovers.

## Deployment and infrastructure

### Hosting and environment layout

- Frontend assets are deployed separately from the backend and served via a CDN-backed static hosting path.  
- Control Plane services and asynchronous evaluators run in a managed Kubernetes cluster.  
- Lab containers are provisioned dynamically into a dedicated isolated namespace or node pool.  
- PostgreSQL is provided through a managed database service.  
- Artifact storage uses object storage with lifecycle and access controls.  
- The platform maintains local, staging, and production environments with clear separation.

### Networking and security

- Ingress traffic terminates with TLS.  
- The learner-facing application and the Control Plane are exposed only through the intended public endpoints.  
- Internal service-to-service traffic is restricted by namespace, network policy, and identity where available.  
- Lab containers use default-deny egress with explicit allowlists.  
- Secrets are stored in a managed secret store and injected at runtime.

### CI/CD and release control

- CI runs tests, static checks, image builds, and security scanning for platform images and lab images.  
- CD promotes versioned manifests through staging into production.  
- Database migrations are version-controlled and applied with explicit rollout ordering.  
- Rollback must be supported for application code and declarative infrastructure changes.  
- Release gates should include security checks, integration tests, and operational readiness validation.

### Backup and restore

- Managed database backups must be enabled and retained according to policy.  
- Restore procedures must be tested periodically.  
- Artifact retention and deletion must align with privacy policy and cost constraints.  
- Audit logs and critical operational records must survive application restarts and routine deployment events. fileciteturn1file0

## Observability

### Tracing

Distributed tracing links learner actions, Control Plane operations, Orchestrator provisioning, Agent Harness tool execution, and evaluator activity under a shared session trace root. Key spans should include session launch latency, model-generation latency, tool-execution latency, and evaluation latency.

### Structured logging

All services should emit structured logs including `session_id`, `lab_id`, `user_id` where appropriate, `trace_root_id`, and component name. Logs from ephemeral lab containers must be exported before container termination.

### Metrics

Core operational metrics include:

- session launch success rate  
- active WebSocket count  
- session provisioning latency  
- model first-token latency  
- evaluator backlog depth  
- quota rejection rate  
- provider error rate  
- lab container crash rate  
- restore test success rate

### Alerting

Critical alerts should cover:

- elevated session-provisioning failures  
- sustained provider outages or latency spikes  
- exhausted lab capacity  
- evaluator backlog beyond threshold  
- database connectivity issues  
- unusually high abuse or quota-trigger rates

## Security and abuse controls

### Runtime containment

- Lab containers run as non-root with dropped Linux capabilities and no privilege escalation.  
- CPU, memory, and storage limits bound the blast radius of runaway execution.  
- No direct credentials for the database, secret store, or internal admin APIs are exposed inside lab containers.

### Authorization and access control

- The Control Plane enforces role-based access for learner and admin operations.  
- Session history, and traces are owner-scoped unless explicitly accessed by an authorized operator.  
- Administrative controls and support actions are auditable.

### Abuse and denial-of-wallet protection

- Edge protections, rate limiting, quotas, and per-session concurrency controls defend against scripted abuse and excessive spend.  
- Suspicious activity signals should support account restriction or temporary disabling.  
- Emergency degraded modes should allow operators to stop launches, or specific expensive labs without taking down the entire platform.

## Testing and validation strategy

A production-facing release requires testing beyond ordinary unit coverage.

### Unit tests

- authorization checks  
- quota calculations  
- lab-policy validation  
- event-ordering utilities  
- evaluator logic for constraint rules

### Integration tests

- session launch through Orchestrator provisioning  
- Control Plane to Agent Harness prompt flow  
- durable trace append and replay  
- evaluator consumption from committed trace records  
- resume behavior for hot and warm-reconstruction labs

### End-to-end tests

- learner can sign in, launch a lab, interact, receive feedback, and review trace history  
- admin can inspect a failed session and disable a lab with audit logging  
- degraded-mode controls correctly block new launches while preserving read access to history

### Security and abuse tests

- object-level authorization tests for sessions, and traces  
- network-egress restriction tests for lab containers  
- attempts to access secrets or control-plane services from inside the lab runtime  
- denial-of-wallet scenarios such as repeated launch spam or prompt flooding

### Resilience and operational tests

- provisioning timeout behavior  
- provider outage simulation  
- evaluator backlog simulation  
- database failover or restore drill in a staging-like environment  
- rollback validation for application and schema changes

The release process should require passing a defined subset of these tests before staging promotion and public rollout.

## Alternatives considered

### Server-Sent Events vs WebSockets

SSE is simpler but does not fit the need to multiplex learner interaction, model output, trace events, and asynchronous tutor feedback over a single active session channel. WebSockets are preferred for the live lab experience.

### Polyglot persistence vs PostgreSQL-first design

A separate document store for traces could improve extreme-scale write throughput, but a PostgreSQL-first design reduces operational overhead and keeps session state, traces, evaluations, and quotas within a manageable transactional boundary for the initial release.

### Serverless containers vs Kubernetes-managed lab containers

Serverless container execution reduces infrastructure overhead but provides less control over low-level runtime isolation, network policy, and lab lifecycle behavior. Kubernetes is preferred because the platform is intentionally executing potentially hostile tool behavior inside labs.

### In-band evaluation vs asynchronous evaluation

Evaluating constraints directly in the session interaction path could simplify data flow but would increase latency and fragility. The evaluation pipeline remains out-of-band so learner interaction stays responsive even if tutor feedback is delayed. fileciteturn1file0

## Rollout plan and milestones

### Phase 1: Core local path

- learner interface scaffold  
- Control Plane session creation and authentication integration  
- local lab container prototype with Agent Harness  
- basic prompt streaming and trace persistence

### Phase 2: Cloud session orchestration

- managed PostgreSQL and object storage  
- Kubernetes-based Orchestrator  
- staging environment deployment  
- first end-to-end remote lab launch

### Phase 3: Evaluation and traceability

- structured trace schema finalized  
- evaluator service consuming trace events  
- learner trace viewer and tutor feedback delivery  
- lab versioning for prompts, tools, and constraints

### Phase 4: Safety and operational hardening

- authorization and audit logging  
- quotas, rate limits, and abuse signals  
- backup/restore validation  
- failure-mode and load testing

### Phase 5: Staged public launch

- allowlisted beta  
- monitored production rollout  
- readiness gates for full public access  
- post-launch tuning based on operational and instructional signals

