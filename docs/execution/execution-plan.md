# Project Execution Plan

**Document Owner:** Kane Walter
**Target Start Date:** TBD
**Target Completion Date:** TBD
**Status:** Draft

## 1\. Executive Summary

This execution plan covers delivery of a V1 AI agent security lab platform suitable for staging validation and initial public beta. The target release is a publicly accessible system where authenticated learners can launch supported labs, interact with an agent inside a fresh isolated runtime, view structured traces and feedback, and where operators retain sufficient controls to manage abuse, failures, and launch risk.

The main delivery constraint is that this is a security-sensitive public system. V1 must therefore prioritize end-to-end correctness of the Control Plane, session lifecycle, runtime isolation, authorization, quota enforcement, and operational readiness over breadth of features or number of labs.

The plan deliberately aims for one thin, reliable vertical slice first, then layers on trace/evaluation, public-exposure controls, and operational hardening. The goal is not to build the full long-term platform in one pass, but to reach a narrow release that is safe, debuggable, and extensible.

## 2\. Scope of V1

The following capabilities are in scope for this execution plan:

- learner authentication and basic account access
- learner-visible lab catalog for a small set of supported labs
- Control Plane APIs for session creation, session metadata, history, and trace retrieval
- WebSocket-based live session interaction for learner prompts and streamed outputs
- durable session lifecycle management using the defined state machine
- fresh isolated lab runtime per session
- Agent Harness that can call the model gateway and execute only approved tools
- structured trace-event capture for session lifecycle, learner prompts, model activity, tool activity, and evaluator outputs
- basic evaluator path for constraint-based feedback on supported labs
- learner-visible session history and trace review
- admin role with bounded operational controls
- role-based access control for learner and admin workflows
- quota and abuse controls for launches, active sessions, prompt volume, and emergency degraded mode
- baseline observability, alerting, audit logging, backup/restore validation, and rollback readiness
- staging deployment and public-beta launch gates

## 3\. Out of Scope for V1

The following are explicitly deferred:

- uploads and artifact-ingestion workflows
- advanced instructor, researcher, or moderator roles
- enterprise SSO and organization management
- multi-region deployment
- advanced analytics, recommendation, or personalization systems
- automated generation of constraint logic from traces
- arbitrary third-party plugins or tool ecosystems outside approved lab contracts
- mobile applications
- large-scale content-moderation systems beyond basic abuse handling and operator intervention
- broad lab library expansion beyond the initial supported V1 set

## 4\. Delivery Principles

- Deliver one thin end-to-end vertical slice before expanding platform breadth.
- Treat session lifecycle correctness as a foundational dependency for most other work.
- Prove sandbox/runtime isolation before exposing the system publicly.
- Capture durable traces before relying heavily on evaluator feedback.
- Keep the first public release narrow in feature scope and lab count.
- Prefer simple, explicit control paths over clever abstractions in V1.
- Operational readiness is part of delivery, not a post-build activity.
- If timeline pressure appears, cut optional UX breadth before cutting security, auditability, or recovery readiness.

## 5\. High-Level Milestones

- **Milestone 1:** Local end-to-end vertical slice
- **Milestone 2:** Cloud Control Plane and sandbox orchestration in staging
- **Milestone 3:** Trace pipeline, evaluator, and learner trace review
- **Milestone 4:** Authorization, quotas, abuse controls, and admin operations
- **Milestone 5:** Operational hardening and staged public beta readiness

## 6\. Workstreams

### 6.1 Learner UI and Trace Viewer

**Objective:** Deliver the learner-facing experience for lab launch, live interaction, history, and trace review.

**Main deliverables:**

- auth-gated learner shell
- lab catalog UI
- session page with prompt/response loop
- live session status display
- learner-visible history and trace viewer
- feedback rendering

**Major dependencies:**

- API and WebSocket contracts
- session lifecycle implementation
- durable trace schema

**Primary owner:** TBD

### 6.2 Control Plane and Session Lifecycle APIs

**Objective:** Implement the trusted backend entry point for session creation, session inspection, state transitions, and WebSocket session control.

**Main deliverables:**

- session lifecycle persistence
- idempotent session launch API
- session metadata/history/trace APIs
- WebSocket session manager
- reconciliation and expiry jobs

**Major dependencies:**

- session lifecycle spec
- auth integration
- database schema

**Primary owner:** TBD

### 6.3 Orchestrator and Sandbox Runtime

**Objective:** Provision and clean up fresh isolated runtimes per session while enforcing baseline runtime restrictions.

**Main deliverables:**

- staging cluster/runtime pool
- lab runtime provisioning path
- baseline runtime profile
- default-deny network policy
- runtime cleanup and orphan handling

**Major dependencies:**

- sandbox/runtime isolation spec
- cloud infrastructure provisioning
- lab image pipeline

**Primary owner:** TBD

### 6.4 Agent Harness and Tool Execution

**Objective:** Execute learner turns inside the runtime, mediate model calls, and emit structured tool/runtime events.

**Main deliverables:**

- model gateway integration
- allowed tool surface for supported labs
- policy-denial path
- structured runtime event emission

**Major dependencies:**

- sandbox runtime
- trace schema
- session streaming path

**Primary owner:** TBD

### 6.5 Trace Pipeline and Evaluator

**Objective:** Capture durable trace events and convert supported event patterns into learner-visible constraint-based feedback.

**Main deliverables:**

- trace persistence
- trace replay path
- evaluator worker
- lab-bound evaluator versioning
- feedback publication path

**Major dependencies:**

- trace schema spec
- session APIs
- supported V1 lab definitions

**Primary owner:** TBD

### 6.6 Authentication and Authorization

**Objective:** Enforce identity, ownership, and admin boundaries across REST and WebSocket paths.

**Main deliverables:**

- auth provider integration
- role resolution
- object-level authorization checks
- admin route protection
- privileged audit logging

**Major dependencies:**

- authorization spec
- Control Plane route implementation

**Primary owner:** TBD

### 6.7 Quota and Abuse Controls

**Objective:** Protect the public system from session spam, runaway usage, and denial-of-wallet behavior.

**Main deliverables:**

- launch quotas
- active-session caps
- prompt-rate limits
- budget guards
- degraded mode controls
- abuse signals and dashboards

**Major dependencies:**

- quota/abuse spec
- session lifecycle APIs
- observability pipeline

**Primary owner:** TBD

### 6.8 Observability, CI/CD, and Operational Readiness

**Objective:** Ensure the platform can be deployed, monitored, restored, and rolled back safely.

**Main deliverables:**

- structured logging and metrics
- alerting for critical failure modes
- CI/CD and image build pipeline
- backup and restore validation
- rollback path
- launch checklist and runbook inputs

**Major dependencies:**

- staging infrastructure
- runtime and Control Plane services
- launch-gate definition

**Primary owner:** TBD

## 7\. Detailed Task Breakdown

### Milestone 1: Local end-to-end vertical slice

| Task ID | Task Name | Workstream | Description | Dependencies | Estimate | Status |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| 1.1 | Session Schema and Lifecycle Wiring | Control Plane | Implement durable session table changes and lifecycle transitions for V1 states. | Session lifecycle spec approved | 1 day | To Do |
| 1.2 | Local Session Launch API | Control Plane | Implement idempotent session creation endpoint and local provisioning handoff. | 1.1 | 1 day | To Do |
| 1.3 | Local Agent Harness Prototype | Agent Harness | Run one local lab runtime that accepts prompts, calls model gateway, and emits structured events. | None | 1 day | To Do |
| 1.4 | Minimal WebSocket Session Stream | Control Plane | Implement basic live stream path for session status and model output. | 1.2, 1.3 | 1 day | To Do |
| 1.5 | Minimal Learner UI Flow | Learner UI | Build lab list, session page, and live prompt/response loop against local backend. | 1.2, 1.4 | 1 day | To Do |
| 1.6 | Initial Trace Persistence | Trace/Evaluator | Persist core lifecycle, prompt, and model events in session order. | 1.3, 1.4 | 1 day | To Do |
| 1.7 | Local End-to-End Smoke Test | Ops / QA | Validate local launch, interaction, trace persistence, and terminal-state handling. | 1.1-1.6 | 1 day | To Do |

### Milestone 2: Cloud Control Plane and sandbox orchestration in staging

| Task ID | Task Name | Workstream | Description | Dependencies | Estimate | Status |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| 2.1 | Staging Infrastructure Provisioning | Ops / Orchestration | Provision staging environment, managed database, runtime pool, and secrets baseline via IaC. | None | 1 day | To Do |
| 2.2 | Control Plane Deployment Path | Ops / Control Plane | Deploy backend services to staging with environment configuration and health checks. | 2.1 | 1 day | To Do |
| 2.3 | Runtime Image Build Pipeline | Sandbox Runtime | Build, version, and publish approved lab runtime images for staging. | 2.1 | 1 day | To Do |
| 2.4 | Baseline Runtime Isolation Policy | Sandbox Runtime | Apply non-root runtime, resource limits, and default-deny egress baseline. | 2.1, 2.3 | 1 day | To Do |
| 2.5 | Orchestrator Provisioning Flow | Orchestrator | Replace local runtime creation with staging runtime provisioning and cleanup. | 2.2, 2.4 | 1 day | To Do |
| 2.6 | Runtime Health and Reconciliation | Control Plane | Detect missing, failed, or orphaned runtimes and reconcile session state. | 2.5 | 1 day | To Do |
| 2.7 | Staging End-to-End Launch Validation | Ops / QA | Validate remote session launch and teardown with baseline restrictions. | 2.2-2.6 | 1 day | To Do |

#### E4-T1 Implementation Notes (Local Staging-Equivalent Baseline)

Implemented baseline staging provisioning with local Kubernetes (`kind`) to satisfy P0-E4-T1 acceptance intent before cloud-managed rollout.

- Staging environment bootstrap path:
  - `kind create cluster --name agent-failure-staging`
  - `bash infra/staging/bootstrap.sh`
- Runtime/control-plane separation:
  - dedicated namespaces: `control-plane` and `runtime-pool`
  - manifests in `deploy/k8s/staging/namespaces.yaml`
- Non-runtime service config/secrets baseline:
  - `ConfigMap` + `Secret` applied in `control-plane`
  - manifest: `deploy/k8s/staging/control-plane-config.yaml`
- Runtime scheduling verification:
  - smoke pod manifest: `deploy/k8s/staging/runtime-smoke-pod.yaml`
  - verification commands:
    - `kubectl get ns control-plane runtime-pool`
    - `kubectl -n runtime-pool get pod runtime-smoke -w`
    - `kubectl -n runtime-pool logs runtime-smoke`
  - observed proof: pod reached `Completed`; logs contained `runtime-scheduling-ok`
- Reproducibility:
  - `infra/staging/bootstrap.sh` applies namespaces, waits for default service accounts, applies config/secrets, and deploys smoke pod
  - runbook: `infra/staging/README.md`
- Current limitations:
  - local `kind` is a staging-equivalent baseline, not managed cloud staging
  - no runtime hardening/egress policy yet (covered by E4-T4/E4-T5)
  - no orchestrator provisioning integration yet (covered by E4-T3)

#### E4-T2 Implementation Notes (Runtime Image Build/Publish Baseline)

Implemented a scriptable runtime image pipeline for the initial supported V1 lab path with digest pinning and staging lock/selection files.

- Runtime image build automation:
  - `scripts/build_runtime_image.sh`
  - builds `runtimes/baseline/Dockerfile`
  - tags image with both release and source tags:
    - `v1-baseline-<lab_version>`
    - `sha-<git_sha>`
  - writes build metadata artifact:
    - `.artifacts/runtime-image-build.env`
- Image scan before promotion:
  - `scripts/scan_runtime_image.sh`
  - gate configured for severity threshold (baseline: `CRITICAL`)
  - writes scan output artifact:
    - `.artifacts/runtime-image-scan.txt`
- Publish path and digest capture:
  - `scripts/push_runtime_image.sh`
  - pushes runtime tags to registry
  - resolves canonical digest reference (`repo@sha256:...`)
  - writes release artifact:
    - `.artifacts/runtime-image-release.env`
- Digest lock for staging consumption:
  - `deploy/k8s/staging/runtime-image.lock`
  - includes digest-pinned image records for `baseline` lab versions
  - includes active and revoked status examples
- Default launch target selection:
  - `deploy/k8s/staging/runtime-image-selection.yaml`
  - default points to active lock entry (`baseline` / `0.1.0`)
  - revoked entry is retained in lock but not selected by default

Suggested command sequence:

- `./scripts/build_runtime_image.sh`
- `./scripts/scan_runtime_image.sh`
- `./scripts/push_runtime_image.sh`
- `./scripts/validate_runtime_lock.sh`

Current limitations:

- baseline pipeline is script-first and local-operator driven (full CI/CD promotion wiring follows later)
- vulnerability gating is currently minimal baseline and can be tightened
- orchestrator consumption of lock selection is implemented in follow-on ticket E4-T3

### Milestone 3: Trace pipeline, evaluator, and learner trace review

| Task ID | Task Name | Workstream | Description | Dependencies | Estimate | Status |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| 3.1 | Trace Event Schema Implementation | Trace/Evaluator | Implement typed durable event envelopes and session-scoped ordering. | Trace schema spec approved | 1 day | To Do |
| 3.2 | Tool and Runtime Event Capture | Agent Harness | Emit structured tool, denial, and runtime events from supported labs. | 3.1, 2.5 | 1 day | To Do |
| 3.3 | Trace Replay API | Control Plane | Expose paginated trace retrieval and learner-visible history path. | 3.1 | 1 day | To Do |
| 3.4 | Basic Evaluator Worker | Trace/Evaluator | Consume committed trace events and emit initial constraint-based evaluation outputs. | 3.1, supported lab definition | 1 day | To Do |
| 3.5 | Feedback Publication Path | Control Plane / Trace | Deliver evaluator outputs to history and live stream. | 3.3, 3.4 | 1 day | To Do |
| 3.6 | Learner Trace Viewer | Learner UI | Render ordered trace events and learner-visible feedback in session history. | 3.3, 3.5 | 1 day | To Do |
| 3.7 | Version-Bound Evaluation Check | Trace/Evaluator | Ensure evaluator uses the exact lab version bound to the session. | 3.4 | 1 day | To Do |

### Milestone 4: Authorization, quotas, abuse controls, and admin operations

| Task ID | Task Name | Workstream | Description | Dependencies | Estimate | Status |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| 4.1 | Identity Provider Integration | Auth | Integrate bearer-token auth and user linkage. | 2.2 | 1 day | To Do |
| 4.2 | Object-Level Authorization Enforcement | Auth / Control Plane | Enforce ownership and admin access across session, history, trace, and stream routes. | 4.1, authorization spec | 1 day | To Do |
| 4.3 | Admin Role and Audit Logging | Auth / Ops | Add admin-protected actions and privileged audit records. | 4.2 | 1 day | To Do |
| 4.4 | Launch Quota Enforcement | Quota/Abuse | Enforce per-user launch quotas, active-session caps, and platform launch controls. | 4.1, quota spec | 1 day | To Do |
| 4.5 | Prompt Admission Controls | Quota/Abuse | Enforce prompt-rate limits, overlapping-turn denial, and session-level budget guards. | 4.4, session stream | 1 day | To Do |
| 4.6 | Degraded Mode Controls | Quota/Abuse / Ops | Add admin controls to block launches or reduce system exposure under stress. | 4.3, 4.4 | 1 day | To Do |
| 4.7 | Admin Session and Lab Controls | Auth / Ops | Implement admin session cancellation and lab disable routes. | 4.3 | 1 day | To Do |
| 4.8 | Abuse Metrics and Dashboards | Ops / Quota | Expose quota denials, suspicious usage, and capacity signals to operators. | 4.4-4.6 | 1 day | To Do |

### Milestone 5: Operational hardening and staged public beta readiness

| Task ID | Task Name | Workstream | Description | Dependencies | Estimate | Status |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| 5.1 | Structured Logging and Metrics Coverage | Ops | Ensure critical components emit logs, metrics, and health indicators with session correlation. | 2.2, 2.5, 3.1 | 1 day | To Do |
| 5.2 | Alerting for Critical Failure Modes | Ops | Configure alerts for launch failures, runtime crashes, provider issues, evaluator backlog, and DB issues. | 5.1 | 1 day | To Do |
| 5.3 | Backup and Restore Validation | Ops | Validate restore path for system-of-record data in a non-production environment. | 2.1 | 1 day | To Do |
| 5.4 | Rollback Validation | Ops / CI-CD | Validate application and migration rollback path in staging. | 2.2, 2.3 | 1 day | To Do |
| 5.5 | Security and Isolation Test Pass | Sandbox Runtime | Run isolation, authorization, and quota-path tests required for launch. | 4.2, 4.5, 2.4 | 1 day | To Do |
| 5.6 | Staging Soak and Failure Drills | Ops / QA | Run staged multi-session testing, degraded mode checks, and selected failure simulations. | 5.1-5.5 | 2 days | To Do |
| 5.7 | Public Beta Launch Review | Cross-functional | Review launch gates, remaining risks, and approve or defer public exposure. | 5.1-5.6 | 1 day | To Do |

## 8\. Dependencies and Critical Path

The major project-level dependencies are:

- session lifecycle implementation must land before stable session APIs and reliable frontend integration
- staging infrastructure and runtime baseline restrictions must land before real multi-user testing
- durable trace capture must exist before evaluator feedback can be trusted
- auth and object-level authorization must be in place before public exposure
- quota and abuse controls must be active before public beta
- observability, restore testing, and rollback validation must complete before launch review

**Likely critical path:**

1. session lifecycle \+ launch API
2. local end-to-end vertical slice
3. staging infrastructure \+ Orchestrator provisioning
4. sandbox isolation baseline
5. trace persistence \+ evaluator path
6. auth \+ authorization
7. quota / abuse controls
8. operational hardening \+ staging soak
9. launch review

## 9\. Phase Exit Criteria

### Milestone 1 Exit Criteria

- a learner can launch a local session end-to-end
- the Control Plane records durable lifecycle transitions
- the Agent Harness can stream model output through the session stream
- core trace events are persisted in session order
- local terminal and failure states behave according to the lifecycle spec

### Milestone 2 Exit Criteria

- staging infrastructure is provisioned through IaC
- the Orchestrator can create and clean up a fresh runtime per session
- baseline runtime restrictions are applied in staging
- failed provisioning and runtime loss surface correctly to logs and session state
- no direct public ingress to lab runtimes exists

### Milestone 3 Exit Criteria

- trace events conform to the V1 schema and are replayable in order
- the evaluator consumes committed events only
- learner-visible feedback can be delivered from evaluator output
- supported labs preserve lab-version-bound evaluation semantics
- learner history and trace review work for completed sessions

### Milestone 4 Exit Criteria

- auth provider integration is functioning for learner and admin users
- ownership checks prevent cross-user access to sessions, traces, and streams
- admin actions are audit logged
- launch quotas and active-session caps are enforced before expensive work begins
- prompt admission controls reject overlapping or excessive turns before model work begins
- degraded mode can block launches and preserve admin access

### Milestone 5 Exit Criteria

- critical logs, metrics, and alerts exist for launch failures, runtime failures, provider failures, and evaluator backlog
- backup and restore path is validated
- rollback path is validated in staging
- required isolation, authorization, and quota tests pass
- staging soak and selected failure drills complete without unresolved critical issues
- launch review has a clear go/no-go outcome

## 10\. Risk Register and Mitigations

| Risk | Impact (H/M/L) | Likelihood (H/M/L) | Mitigation Strategy | Owner |
| :---- | :---- | :---- | :---- | :---- |
| Sandbox/runtime hardening takes longer than expected | High | Medium | Keep a single strict baseline runtime profile for V1 and limit supported labs. | TBD |
| Session semantics churn blocks parallel work | High | Medium | Treat lifecycle, API, and auth specs as locked inputs before full implementation starts. | TBD |
| External model provider instability slows integration and testing | Medium | Medium | Build provider-failure handling, retries, and degraded-mode messaging early. | TBD |
| Quota and abuse controls arrive too late for safe public testing | High | Medium | Make launch quotas and prompt admission controls a milestone, not a polish item. | TBD |
| Observability is insufficient to debug staging failures | High | Medium | Treat logs/metrics/correlation IDs as required work in Milestones 2–5. | TBD |
| Evaluator correctness is lower than expected | Medium | Medium | Keep V1 evaluator narrow and lab-specific; rely on durable traces for debugging and iteration. | TBD |
| Scope expands through too many labs or roles | High | Medium | Lock V1 to a small lab set and learner/admin roles only. | TBD |
| Restore/rollback is untested when launch pressure arrives | High | Low | Require restore and rollback validation as explicit launch gates. | TBD |

## 11\. Launch / Completion Criteria

The project will be considered complete for V1 public beta when all of the following are true:

- learners can authenticate and launch supported labs end-to-end
- every session runs in a fresh isolated runtime with enforced baseline restrictions
- durable traces are captured and replayable for supported labs
- constraint-based feedback works for the supported V1 lab set
- RBAC is enforced for learner and admin workflows
- quota and abuse controls are active for launch and prompt paths
- admin operational controls are available and audit logged
- staging restore test and rollback path have been validated
- critical operational dashboards and alerts exist
- a runbook or operational-readiness package exists for the chosen release target
- launch gates have been reviewed and approved

## 12\. Public Launch Gates

The following gates must be satisfied before public beta:

- sandbox/runtime isolation tests passing
- session lifecycle and prompt-admission tests passing
- authorization tests passing
- trace replay and evaluator-path tests passing for supported labs
- quota and denial-of-wallet protections enabled
- degraded mode and admin containment controls functioning
- privileged audit logging enabled
- restore test successful for critical data stores
- staging soak completed without unresolved critical issues
- rollout and rollback path validated
- launch review completed with explicit approval

If the release target is reduced to closed alpha rather than public beta, some gates may be waived, but any waiver must be recorded explicitly.

## 13\. Open Questions and Deferred Decisions

- exact cloud provider and managed-service choices
- whether model calls remain inside the runtime or move behind a mediated service path later
- whether evaluator triggering is DB-backed, queue-backed, or hybrid in V1
- whether one strict runtime profile is sufficient for all V1 labs
- how many labs should be included in the first public beta
- whether public beta should be allowlisted before fully open exposure
- exact SLO targets to adopt for staging-to-beta promotion

## 14\. Suggested Usage Notes

This execution plan should be used as the delivery glue across the PRD, TDD, and subsystem specs.

Recommended workflow:

1. derive implementation epics and tickets from the milestone task tables
2. link each risky task to the relevant low-level spec
3. update status, dependencies, and risks weekly
4. keep V1 scope tight when new ideas appear
5. use phase exit criteria and launch gates as the decision framework for release readiness

The purpose of this document is sequencing, dependency management, and safe release planning. It should remain compact and should not duplicate architecture detail already captured elsewhere.
