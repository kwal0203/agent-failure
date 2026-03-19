# Product Requirements Document

## Objective

Build a publicly accessible AI agent security lab platform where learners can practice realistic attacks and defenses against LLM agents in controlled, instrumented environments. The product will let learners interact with labs involving prompt injection, retrieval misuse, tool misuse, constrained file operations, and agent reasoning over sandboxed system state, while receiving structured feedback derived from observable outcomes and constraint violations.

The platform must support safe public deployment, reliable production operation, and detailed trace capture for learning, debugging, evaluation, and future improvement of lab design. Each learner session must run in a fresh lab container with strict isolation from other sessions and from platform control-plane services. The product must give operators enough visibility and control to manage failures, abuse, policy violations, and provider outages without weakening the safety model of the labs.

The objective is not to build a general-purpose chat application or unrestricted coding sandbox. The objective is to deliver a production-grade instructional cyber range for AI agent security where learners can experiment inside deliberately constrained environments, see the consequences of agent actions, and receive feedback that is grounded in the actual state of the lab.

## Target audience

Primary users are learners who want hands-on practice with AI agent security concepts, especially prompt injection, indirect prompt injection, retrieval-augmented failure modes, unsafe tool use, constrained execution, and defense-oriented reasoning in agentic systems.

Secondary users are instructors, mentors, and researchers who need to review learner traces, inspect session outcomes, compare behavior across lab runs, and evaluate whether labs are producing useful learning signals.

Operational users are platform operators and administrators who need privileged access to platform health, lab runtime status, audit logs, abuse signals, and incident controls. Administrative access must be limited by role and fully auditable.

## User flow

1. A learner visits the public web application and creates an account or signs in.
2. The platform authenticates the learner, establishes a session, and applies role-based authorization.
3. The learner browses the lab catalog and selects a specific lab, such as a prompt injection lab, tool misuse lab, or retrieval-enabled lab.
4. The Orchestrator provisions a fresh lab container for the selected lab, initializes the lab state, applies the lab definition and constraint set, and starts an agent harness for the session.
5. The learner interacts with the lab through a React-based interface that may expose lab instructions, agent traces, file views, retrieval panels, structured feedback, and session state.
6. The agent harness sends prompts to an LLM backend and executes only the tool calls allowed by the lab contract against the sandboxed environment.
7. The platform records structured events for learner prompts, model responses, tool calls, tool outputs, constraint checks, environment telemetry, success signals, and policy denials.
8. The learner receives feedback through lab-specific success criteria, trace inspection, and constraint-based signals such as unsafe action attempts, failed exploit chains, or successful defensive actions.
9. If the session is interrupted, the platform preserves session state according to the lab’s resume policy.
10. At the end of the run, the learner can review the trace, outcomes, and feedback permitted by the lab and product policy.
11. Authorized operators can inspect failed sessions, review runtime health, moderate abuse, and use emergency controls if the platform is under attack or degraded.

## Assumptions and constraints

- The product will be deployed publicly and must assume adversarial usage, automated abuse, and repeated attempts to probe isolation boundaries.
- Every learner session must run in a fresh lab container with no shared writable state across learners.
- Lab containers must be isolated from the control plane, persistent stores, secrets, and administrative services.
- By default, lab containers must not have outbound internet access except to explicitly approved destinations required for the product to function.
- The platform may depend on third-party LLM providers through a gateway such as OpenRouter and must tolerate degraded provider behavior or temporary outages.
- The system must distinguish between authentication and authorization; signing in alone must not grant access to other users’ sessions, traces, or administrative workflows.
- The platform must separate development, staging, and production environments.
- Production secrets, credentials, and user data must not be exposed to development or staging environments.
- Learner traces, and logs may contain sensitive user-generated content and must be governed by documented retention and deletion policies.
- Exact infrastructure layout, backup implementation, deployment mechanics, and incident procedures will be specified in the technical design document and runbook, but the PRD must define the product-level requirements those documents must satisfy.

## Functional requirements (in scope)

### Account access and authorization

- The platform shall support secure account creation, sign-in, session management, and logout.
- The platform shall enforce role-based access control so learners can access only their own lab sessions, traces, and results.
- The platform shall support at least learner and administrator roles for the initial release, with the ability to add instructor or researcher roles later.
- Administrative and support actions shall be auditable.

### Lab catalog and session lifecycle

- The platform shall allow authenticated learners to browse and launch available labs from a lab catalog.
- The Orchestrator shall provision a fresh lab container for each new session.
- Each session shall be initialized to a lab-specific starting state defined by the lab contract.
- The platform shall define session lifecycle states including created, provisioning, active, idle, expired, completed, and failed.
- The platform shall define idle timeout, maximum session duration, and expiry behavior.
- The platform shall support resume behavior for labs that permit it.
- The platform shall define exactly what session state is preserved on resume, including whether the prior lab container is resumed, reconstructed, or replaced with preserved artifacts and trace state.

### Learner interaction and trace visibility

- The platform shall provide a browser-based interface for lab instructions, learner prompts, model outputs, trace inspection, and feedback.
- The interface shall expose relevant agent actions, tool invocations, and environment observations where appropriate for the instructional goals of the lab.
- The platform shall provide learner-visible feedback events such as success, failure, constraint violations, denied actions, hints, and progress signals.
- The interface shall communicate clearly when a learner action, tool attempt, or session transition is rejected due to lab policy or platform constraints.

### Agent harness and tool execution

- Learner interactions shall be routed through an Orchestrator and agent harness that manage model calls, tool calls, and lab-state interactions.
- Each lab shall define an approved tool surface and associated constraints.
- The agent harness shall execute only the tool calls allowed by the active lab contract.
- Tool execution shall follow least-privilege principles.
- The platform shall log tool invocations, tool outputs, policy denials, and major environment state changes as structured events.
- The platform shall support lab-specific prompt scaffolding, tool policy, success conditions, and feedback logic.

### Constraint-based feedback and evaluation

- The platform shall support feedback based on observable constraint violations and state changes rather than only free-form textual judgment.
- Labs shall be able to define success signals, failure signals, and instructional feedback triggers.
- The platform shall support structured evaluation outputs for whether a learner or agent action succeeded, partially succeeded, violated a constraint, or triggered a disallowed path.
- Feedback and evaluation logic shall be versioned with the lab definition.

### Trace capture, history, and reproducibility

- The platform shall record structured traces for learner prompts, model outputs, tool calls, tool outputs, environment telemetry, policy decisions, feedback events, and major session state transitions.
- Learners shall be able to review their own session traces and outcomes subject to product policy.
- Authorized staff shall be able to inspect traces for support, moderation, research, and debugging, subject to role and audit controls.
- The platform shall version lab definitions, system prompts, constraint sets, tool contracts, and evaluation logic so that historical runs remain interpretable.

### Abuse prevention, quotas, and cost control

- The platform shall enforce per-user and platform-level controls to limit abuse and protect compute and model spend.
- The platform shall support rate limiting, concurrency limits, session creation controls, token or request budgets, and session duration caps.
- The platform shall support detection of suspicious patterns such as scripted account creation, repeated rapid session launches, anomalous prompt volume, or attempts to trigger excessive model usage.
- Authorized administrators shall be able to restrict, suspend, or otherwise limit abusive accounts.

### Administrative and support workflows

- The platform shall provide authorized operators with internal workflows to inspect runtime health, review failed sessions, investigate abuse, and diagnose incidents.
- The platform shall expose audit logs for privileged actions.
- The platform shall support emergency controls such as disabling new lab launches, limiting provider usage, or otherwise placing the platform into a safer degraded mode during an incident.

### Privacy, retention, and deletion

- The platform shall define retention categories for accounts, lab traces, logs, telemetry, and audit records.
- The platform shall define deletion behavior for user-generated data and expired session artifacts.
- The platform shall disclose to learners what data is stored, why it is stored, and how long it is retained.
- The platform shall support the product’s privacy and consent model for public deployment.

## Non-functional requirements (in scope)

### Security and isolation

- Every lab session must execute in a fresh isolated lab container with no shared writable state across learners.
- The Orchestrator, databases, audit stores, secret stores, and other control-plane services must remain isolated from untrusted lab execution.
- Lab containers must use default-deny outbound networking, with only explicitly approved destinations allowed.
- The platform must prevent unauthorized access to lab sessions, traces, administrative workflows, and internal services.
- Production secrets and credentials must be stored and managed securely.
- Privileged actions must be auditable.

### Reliability and availability

- The platform must define target availability and key operational success indicators for public launch.
- The Orchestrator, persistence layer, and trace pipeline must tolerate common retryable failures without corrupting session state.
- Critical provisioning and persistence operations must support retries and idempotency where feasible.
- The platform must support backup and restore capability for durable system-of-record data.
- The system must define recovery expectations for service outages, storage failures, and provider degradation.

### Performance

- Session provisioning, learner interaction, trace rendering, and feedback delivery must meet latency targets appropriate for interactive use.
- The platform must define acceptable performance targets for session launch, time to first model response, feedback rendering, and operator trace inspection.
- The platform must maintain acceptable user experience under expected concurrent learner load.

### Scalability

- Stateless control-plane services should scale horizontally where appropriate.
- The platform must support bounded scaling of lab containers while preserving isolation and cost controls.
- The platform must define capacity assumptions for concurrent learners, concurrent lab sessions, trace volume, and model request throughput.

### Observability and auditability

- The platform must expose logs, metrics, traces, health indicators, and audit records sufficient for debugging, monitoring, and incident response.
- Operators must be able to diagnose failed provisioning, stuck lab containers, repeated policy denials, elevated model errors, degraded provider performance, and abnormal abuse signals.
- The platform must support audit logs for authentication events, privileged actions, policy denials, quota enforcement, and key configuration changes.

### Data management and schema evolution

- Durable system-of-record data must be persisted in a managed database with migration support.
- The platform must define retention, archival, and deletion handling for traces, logs, and telemetry.
- Event schemas, session records, and lab metadata must support evolution without breaking core product behavior or making historical runs uninterpretable.
- Lower environments must not rely on unrestricted access to production user data.

### Release and environment management

- The platform must maintain separate development, staging, and production environments.
- The platform must support controlled deployment, rollback capability, and pre-production validation.
- Public launch must require defined readiness gates across security, performance, observability, and operational preparedness.

### Compliance, policy, and public deployment readiness

- The platform must provide clear user-facing disclosures around acceptable use, privacy, retention, and logging.
- The platform must support operator-visible incident readiness, including the ability to suspend risky functionality during an active issue.
- The product must be deployable in a manner consistent with its educational purpose and lawful intended use.

## Out of scope

- Unrestricted shell access or arbitrary outbound internet access from lab containers.
- A general-purpose cloud development environment outside the needs of defined labs.
- Multi-user collaboration inside the same live lab container.
- A full monetization or billing platform beyond the quotas and entitlement controls required for safe public launch.
- Enterprise SSO, advanced organization management, and large-scale B2B administration for the initial release.
- Native mobile applications.
- Arbitrary third-party plugins, external tools, or unreviewed tool integrations outside the approved lab contract model.
- Large-scale recommendation or personalization systems beyond basic learning and operational insight.

## Success metrics/Definition of done

The initial release will be considered done when:

- Learners can securely sign in, launch supported labs, and complete end-to-end lab runs through the public web application.
- Each lab run is provisioned in a fresh isolated lab container with enforced tool and network restrictions.
- Learner prompts, model outputs, tool calls, tool outputs, feedback events, and key environment transitions are captured in structured traces.
- Learners can review their own session outcomes and traces, and authorized staff can inspect traces through controlled administrative workflows.
- The platform enforces role-based access control, rate limiting, session quotas, and basic abuse controls appropriate for public exposure.
- Production observability is sufficient to detect failed provisioning, elevated error rates, provider outages, stuck sessions, and abusive usage patterns.
- Durable data is backed up and there is a tested restore path for critical stores.
- Retention, deletion, privacy, and acceptable-use policies are defined and reflected in user-visible behavior.
- Development, staging, and production environments are separated and controlled rollback is supported.

Key launch metrics should include:

- lab session launch success rate
- lab completion rate
- p95 session provisioning latency
- p95 time to first model response
- p95 feedback rendering latency
- failed or abandoned session rate
- false positive and false negative rates for key constraint-based evaluation signals where measurable
- critical incident count and mean time to recovery
- quota trigger rate and abuse-detection rate
- backup restore test success for critical data stores

## Risks

### Isolation and security risk

A public AI agent security lab platform may attract deliberate misuse, repeated probing, or attempts to cross isolation boundaries. This risk is mitigated through fresh lab containers per session, strict network controls, least-privilege tool contracts, secure secret handling, audit logging, and emergency operator controls.

### Abuse and cost risk

Public users may attempt scripted signups, session spam, token burning, or other denial-of-wallet behavior. This risk is mitigated through quotas, rate limits, provider budget controls, suspicious activity detection, and administrative account restriction workflows.

### Reliability risk

Provisioning failures, trace pipeline issues, storage errors, or upstream LLM provider degradation may disrupt learner sessions. This risk is mitigated through retries, idempotent operations where feasible, strong observability, degraded-mode handling, and clear operational procedures.

### Data and privacy risk

Learner traces may contain sensitive user-generated content. This risk is mitigated through access controls, retention limits, secure storage, deletion policies, and transparent user disclosures.

### Operational risk

Without adequate operator workflows and incident controls, public incidents may be difficult to detect or contain. This risk is mitigated through administrative observability, auditable privileged actions, backup and restore readiness, environment separation, and incident-response preparation.

### Instructional risk

If labs are brittle, traces are confusing, or feedback signals are too noisy, learners may not trust the platform or may fail to learn from the exercises. This risk is mitigated through careful lab design, explicit interface messaging, versioned evaluation logic, measurable feedback-quality targets, and staged rollout before broad public launch.

## Milestones

### Milestone 1: Core lab platform foundation

- public web application shell
- learner authentication and session management
- initial lab catalog and lab launch flow
- Orchestrator and fresh lab container provisioning
- initial agent harness and constrained tool execution

### Milestone 2: Traceability and learner review

- durable session records
- structured trace pipeline
- learner-visible trace and outcome review
- initial constraint-based feedback and evaluation framework
- resume support for selected labs

### Milestone 3: Public deployment safety controls

- role-based authorization and privileged audit logging
- rate limiting, quotas, and abuse controls
- environment separation across development, staging, and production
- production observability baseline

### Milestone 4: Operational readiness

- administrative support and moderation workflows
- backup and restore capability
- incident controls and degraded-mode handling
- retention and deletion policy implementation
- launch readiness validation across security, performance, and operations

### Milestone 5: Public launch

- staged rollout through staging or beta
- monitored public availability
- rollback readiness
- post-launch review of operational metrics, abuse signals, and learner outcomes
