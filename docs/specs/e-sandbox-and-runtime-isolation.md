# Sandbox and Runtime Isolation Specification

## Purpose

This document defines the isolation boundary, runtime restrictions, and orchestration requirements for lab execution in the AI agent security lab platform. Its purpose is to ensure that every learner session runs inside a constrained environment that is suitable for instruction while remaining safe for public deployment.

This specification is lower-level than the PRD and TDD. It describes the security boundary of the lab container, what the runtime may and may not access, how the Orchestrator provisions and tears down lab environments, and what controls must exist to contain misuse, reduce blast radius, and preserve platform integrity.

## Scope

This specification covers:

- isolation goals and threat assumptions
- runtime boundary definition
- container and pod security restrictions
- filesystem and process restrictions
- network ingress and egress rules
- secret and credential boundaries
- runtime identity and service access
- orchestration requirements for lab lifecycle
- logging and observability from ephemeral runtimes
- failure handling and containment rules
- testing requirements for isolation controls

This specification does not define:

- the exact Kubernetes manifest syntax
- cloud-provider-specific firewall syntax
- detailed host hardening outside the runtime boundary
- lab-specific instructional content

## Core principles

- Every learner session must run in a fresh isolated runtime.
- The runtime is untrusted by default, even when the learner is benign.
- The lab runtime must be treated as a containment boundary, not as part of the trusted control plane.
- The runtime must have only the minimum privileges and connectivity required for the active lab contract.
- A compromised or misbehaving runtime must have bounded blast radius.
- Runtime restrictions must be enforced by infrastructure and policy, not only by application logic.
- The Control Plane, database, secret store, and admin interfaces must never rely on the lab runtime being honest.

## Threat assumptions

The initial public deployment must assume at least the following:

- learners may intentionally try to escape the sandbox
- model behavior may trigger unintended tool actions
- repeated prompts may be used to probe restrictions
- the runtime may attempt to access network destinations outside the lab contract
- the runtime may attempt to consume excessive CPU, memory, or storage
- the runtime may attempt to read metadata endpoints, internal services, or mounted credentials
- malicious or malformed lab behavior may crash the runtime

The platform does not assume a nation-state or kernel-zero-day adversary for V1, but it must still defend against realistic public-internet abuse and common container-misconfiguration failures.

## Runtime boundary definition

A lab runtime consists of the per-session execution environment created by the Orchestrator for one learner session.

A runtime includes:

- one session-scoped container or tightly scoped pod
- the Agent Harness process
- lab-specific files and instructional assets required for the lab
- temporary working storage needed for the session
- the minimal network path required to reach approved external services, if any

A runtime does not include:

- the Control Plane
- PostgreSQL or any durable system-of-record database
- the secret store
- admin dashboards or audit systems
- direct cloud-provider control APIs

## Isolation model

### Session isolation

- Each session receives a fresh runtime.
- No writable state may be shared across sessions.
- One learner session must never be attached to another learner’s runtime.
- Runtime names, IDs, and scheduling metadata must not be treated as access tokens.

### Control-plane isolation

- Lab runtimes must not have direct network or credential access to the Control Plane’s privileged internal APIs.
- The Control Plane must interact with runtimes through narrowly scoped channels under platform control.
- A runtime must never be trusted to report its own authorization state.

### Namespace and scheduling isolation

- Lab runtimes should run in a dedicated namespace, pool, or equivalent isolation domain separated from control-plane services.
- Scheduling policy should avoid co-locating sensitive control-plane components with untrusted lab runtimes where feasible.
- The platform should support draining or disabling the runtime pool independently of the control plane during incidents.

## Runtime configuration baseline

### Container user and privileges

- Containers must run as non-root.
- Privilege escalation must be disabled.
- Linux capabilities should be dropped unless a specific capability is explicitly required and approved.
- Host namespaces must not be shared.
- Privileged containers are forbidden.

### Filesystem restrictions

- Root filesystem should be read-only where the lab design allows.
- Writable paths must be explicitly defined and bounded.
- HostPath mounts are forbidden.
- Sensitive host filesystems and control sockets must never be mounted.
- Temporary writable storage must be scoped to the session and removed on cleanup.

### Process restrictions

- PID limits should be configured to reduce fork-bomb or runaway-process risk.
- CPU and memory limits must be enforced.
- Ephemeral storage limits must be enforced.
- Untrusted processes inside the runtime must not gain additional privileges through setuid or similar mechanisms.

### Image provenance

- Runtime images must come from approved registries only.
- Images should be versioned and pinned by digest for published lab versions.
- Image scanning should run before deployment to staging or production.
- A disabled or revoked image must not be launchable for new sessions.

## Network policy

### Ingress

- Direct public ingress to lab runtimes is forbidden.
- Learner interaction flows through the Control Plane rather than connecting directly to the lab container.
- Admin access to a runtime for debugging must not exist as an ad hoc public pathway.

### Egress

- Default-deny egress is required.
- Only explicitly approved outbound destinations may be allowed.
- For V1, the runtime should allow only the minimum path needed for model access through the approved gateway if the Agent Harness performs model calls from inside the runtime.
- Metadata endpoints, cloud control APIs, cluster-internal admin services, and unrelated internet destinations must be blocked.

### DNS

- DNS resolution should be restricted to the minimum required for approved destinations.
- Runtime DNS configuration must not allow easy discovery of internal service topology beyond what is unavoidable.

### Internal service reachability

- Runtimes must not be able to reach PostgreSQL directly.
- Runtimes must not be able to reach the secret store directly.
- Runtimes must not be able to call admin-only Control Plane endpoints.
- If a runtime needs to emit events or heartbeats, that channel must be explicitly scoped and authenticated for that purpose only.

## Secret and credential boundaries

### General rule

No long-lived privileged credentials may be present in the runtime.

### Forbidden in runtime

- database passwords
- secret-store credentials
- cloud account credentials for broad resource access
- admin API tokens
- signing keys

### Allowed credentials

If the runtime must authenticate to a narrow service, it may receive only the minimum-scoped, short-lived credential required for that action.

Examples may include:

- a narrow token for emitting session events to a dedicated ingest path
- a narrow token for reaching the model gateway if model calls are initiated inside the runtime

### Credential handling rules

- credentials must be injected at runtime, not baked into images
- credentials must be rotatable without rebuilding lab images
- credentials must be scoped to the session or runtime class where feasible
- runtime logs and traces must not expose credential values

## Runtime-to-platform communication

### Allowed channels

Any communication from the runtime to trusted platform services must go through explicit, narrow interfaces.

Possible allowed channels include:

- event emission to a dedicated trace-ingest endpoint
- liveness or readiness status to the Orchestrator path
- model-gateway access to an approved external service if the architecture places model calls inside the runtime

### Disallowed patterns

- arbitrary service discovery across the cluster
- generic internal API reachability
- direct database writes from the runtime
- direct audit-log writes from the runtime
- direct admin-control invocation from the runtime

### Trust model

Messages from the runtime are inputs to the trusted platform, not proof of correctness. The Control Plane and other trusted services must validate and contextualize runtime-originated data.

## Orchestrator requirements

### Provisioning

The Orchestrator must:

- create a fresh runtime for each new session
- apply the correct image digest for the session’s lab version
- apply resource limits, network policy, and runtime identity controls
- attach only approved lab assets and temporary storage
- report readiness, failure, and termination events to the Control Plane

### Cleanup

The Orchestrator must:

- terminate runtimes for terminal sessions
- clean up session-scoped storage and temporary resources
- retry cleanup for orphaned runtimes
- surface cleanup failures to operators

### Isolation-aware controls

The Orchestrator must support:

- disabling launches for a lab image or lab version
- halting creation of new runtimes globally during incidents
- draining the runtime pool independently of the control plane
- identifying duplicate or orphaned runtimes tied to a session

## Observability from ephemeral runtimes

### Logging

- Runtime logs required for debugging or trace reconstruction must be exported before teardown where feasible.
- Logs should be structured where possible and tagged with `session_id`, `lab_id`, and runtime identity metadata.
- Sensitive values must be redacted before logs become broadly accessible.

### Metrics

The platform should collect at least:

- runtime launch count
- readiness success/failure count
- runtime crash count
- OOM kill count
- CPU, memory, and ephemeral-storage saturation indicators
- network-policy denial counts where feasible

### Trace relationship

Runtime-originated events that matter instructionally or operationally should appear as durable trace events or be correlated to the session trace root so that debugging does not depend on ephemeral container access.

## Failure handling and containment

### Runtime crash

If the runtime crashes, the Orchestrator reports the crash and the Control Plane transitions the session according to the lifecycle spec.

### Policy violation or repeated denial

Repeated policy denials from a runtime may indicate either a learner exploring the boundary or a broken lab/tool contract. The platform should surface these signals operationally without granting the runtime extra access.

### Suspected isolation breach

If the platform suspects that a runtime has escaped intended restrictions or reached forbidden destinations:

- mark the condition critical
- stop or isolate affected runtimes
- disable new launches for the affected lab or runtime class if necessary
- preserve relevant logs and audit records
- require operator review before resuming normal launch behavior

### Resource exhaustion

If a runtime exceeds configured CPU, memory, PID, or storage limits:

- the resource control should enforce the limit
- the resulting failure should be classified and surfaced
- the platform should not silently retry indefinitely if the lab image or contract is misconfigured

## Compatibility with instructional design

Isolation controls must still allow legitimate lab behavior.

Therefore:

- lab contracts must explicitly declare the minimal runtime capabilities they require
- exceptions to the baseline isolation policy must be deliberate, reviewed, and versioned with the lab
- the default runtime profile should be restrictive, and labs should opt into additional capabilities only when justified

## Minimum runtime profiles

The platform should define at least a baseline profile for V1.

### Baseline profile

Suitable for most labs.

- non-root container
- no privilege escalation
- dropped capabilities
- bounded CPU, memory, PID, and storage
- no direct public ingress
- default-deny egress with only approved model-gateway destination if needed
- no uploads in V1
- no durable writable shared storage

### Future extended profiles

If future labs require additional controlled capability, those should be expressed as named profiles rather than ad hoc exceptions.

Examples might include:

- retrieval-enabled profile
- special filesystem-observation profile
- controlled multi-process profile

These are future-facing and should remain reviewed and versioned.

## Security review checklist

Before a lab version is published to staging or production, the runtime configuration should be reviewed for:

- correct image digest and provenance
- correct runtime profile selection
- no forbidden mounts
- no forbidden credentials
- correct egress allowlist
- correct resource limits
- expected teardown behavior
- observability coverage for failures

## Testing requirements

### Isolation tests

- runtime cannot reach PostgreSQL
- runtime cannot reach secret store
- runtime cannot reach admin-only APIs
- runtime cannot reach disallowed internet destinations
- runtime does not run as root
- runtime cannot escalate privileges

### Resource-control tests

- CPU and memory limits are enforced
- PID limits prevent runaway process creation
- ephemeral-storage limits are enforced
- terminal session cleanup removes runtime and temp storage

### Orchestration tests

- new session gets a fresh runtime
- failed provisioning is surfaced correctly
- duplicate runtime detection works
- disabled lab version cannot launch new runtimes

### Incident-path tests

- global launch disable blocks new runtimes
- suspected-isolation-breach workflow can halt affected runtime class
- cleanup retries surface orphaned runtime failures

## Open implementation choices

The following implementation details may vary as long as this contract remains true:

- whether each session uses a single container or a tightly scoped multi-container pod
- whether model calls occur from inside the runtime or through a more mediated sidecar/service pattern
- whether runtime event emission uses an internal service endpoint or a scoped external ingest path
- exact namespace, node-pool, or runtime-class strategy used to separate lab execution from control-plane services

## Summary

This specification ensures that every lab session runs inside a fresh, constrained, and operationally manageable runtime that is isolated from other sessions and from the trusted platform. Any implementation that grants broad network reachability, embeds privileged credentials in the runtime, allows direct public ingress to lab containers, or treats the runtime as trusted is non-compliant with the platform design.
